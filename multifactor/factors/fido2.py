from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt

from fido2 import cbor
from fido2.client import ClientData
from fido2.server import Fido2Server, PublicKeyCredentialRpEntity
from fido2.ctap2 import AttestationObject, AuthenticatorData
from fido2.utils import websafe_decode, websafe_encode
from fido2.ctap2 import AttestedCredentialData
import logging

from ..models import UserKey, KEY_TYPE_FIDO2
from ..common import render, write_session, login
from ..app_settings import mf_settings


logger = logging.getLogger(__name__)


@login_required
def start(request):
    return render(request, "multifactor/FIDO2/add.html", {})


@login_required
def auth(request):
    return render(request, "multifactor/FIDO2/check.html", {})


def get_server():
    rp = PublicKeyCredentialRpEntity(mf_settings['FIDO_SERVER_ID'], mf_settings['FIDO_SERVER_NAME'], mf_settings['FIDO_SERVER_ICON'])
    return Fido2Server(rp)


@login_required
def begin_registration(request):
    server = get_server()
    registration_data, state = server.register_begin(
        {
            'id': request.user.get_username().encode("utf8"),
            'name': (request.user.get_full_name()),
            'displayName': request.user.get_username(),
        },
        get_user_credentials(request)
    )
    request.session['fido_state'] = state

    return HttpResponse(cbor.encode(registration_data), content_type='application/octet-stream')


@csrf_exempt
@login_required
def complete_reg(request):
    try:
        data = cbor.decode(request.body)

        client_data = ClientData(data['clientDataJSON'])
        att_obj = AttestationObject((data['attestationObject']))
        server = get_server()
        auth_data = server.register_complete(
            request.session['fido_state'],
            client_data,
            att_obj
        )
        encoded = websafe_encode(auth_data.credential_data)
        key = UserKey.objects.create(
            user=request.user,
            properties={
                "device": encoded,
                "type": att_obj.fmt,
                "domain": request.get_host(),
            },
            key_type=KEY_TYPE_FIDO2,
        )
        write_session(request, key)
        messages.success(request, 'FIDO2 Token added!')
        return JsonResponse({'status': 'OK'})

    except Exception:
        logger.exception("Error completing FIDO2 registration.")
        return JsonResponse({
            'status': 'ERR',
            "message": "Error on server, please try again later",
        })


@login_required
def get_user_credentials(request):
    return [
        AttestedCredentialData(websafe_decode(uk.properties["device"]))
        for uk in UserKey.objects.filter(
            user=request.user,
            key_type=KEY_TYPE_FIDO2,
            properties__domain=request.get_host(),
            enabled=True,
        )
    ]


@login_required
def authenticate_begin(request):
    server = get_server()
    auth_data, state = server.authenticate_begin(get_user_credentials(request))
    request.session['fido_state'] = state
    return HttpResponse(cbor.encode(auth_data), content_type="application/octet-stream")


@csrf_exempt
@login_required
def authenticate_complete(request):
    server = get_server()
    data = cbor.decode(request.body)
    credential_id = data['credentialId']
    client_data = ClientData(data['clientDataJSON'])
    auth_data = AuthenticatorData(data['authenticatorData'])
    signature = data['signature']

    cred = server.authenticate_complete(
        request.session.pop('fido_state'),
        get_user_credentials(request),
        credential_id,
        client_data,
        auth_data,
        signature
    )

    keys = UserKey.objects.filter(
        user=request.user,
        key_type=KEY_TYPE_FIDO2,
        enabled=True,
    )

    for key in keys:
        if AttestedCredentialData(websafe_decode(key.properties["device"])).credential_id == cred.credential_id:
            write_session(request, key)
            res = login(request)
            return JsonResponse({'status': "OK", "redirect": res["location"]})

    return JsonResponse({'status': "err"})
