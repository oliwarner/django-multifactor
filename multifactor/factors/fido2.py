from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt

from fido2 import cbor
from fido2.client import ClientData
from fido2.server import Fido2Server, RelyingParty
from fido2.ctap2 import AttestationObject, AuthenticatorData
from fido2.utils import websafe_decode, websafe_encode
from fido2.ctap2 import AttestedCredentialData
import logging

from ..models import UserKey, KEY_TYPE_FIDO2
from ..common import render, write_session, login
from ..app_settings import mf_settings


logger = logging.getLogger(__name__)


SESSION_KEY = 'multifactor_fido_state'

SERVER = Fido2Server(
    rp=RelyingParty(
        ident=mf_settings['FIDO_SERVER_ID'],
        name=mf_settings['FIDO_SERVER_NAME'],
        icon=mf_settings['FIDO_SERVER_ICON']
    )
)


def get_credentials(user):
    return [
        AttestedCredentialData(websafe_decode(uk.properties["device"]))
        for uk in UserKey.objects.filter(user=user, key_type=KEY_TYPE_FIDO2)
    ]


@login_required
def start(request):
    return render(request, "multifactor/FIDO2/add.html", {})


@login_required
def auth(request):
    return render(request, "multifactor/FIDO2/check.html", {})


@login_required
def begin_registration(request):
    registration_data, state = SERVER.register_begin(
        {
            'id': request.pk,
            'name': request.user.get_username(),
            'displayName': request.user.get_full_name(),
        },
        get_credentials(request.user)
    )
    request.session[SESSION_KEY] = state

    return HttpResponse(cbor.encode(registration_data), content_type='application/octet-stream')


@csrf_exempt
@login_required
def complete_reg(request):
    try:
        data = cbor.decode(request.body)
        att_obj = AttestationObject(data['attestationObject'])
        auth_data = SERVER.register_complete(
            state=request.session[SESSION_KEY],
            client_data=ClientData(data['clientDataJSON']),
            attestation_object=att_obj,
        )
        key = UserKey.objects.create(
            user=request.user,
            properties={
                "device": websafe_encode(auth_data.credential_data),
                "type": att_obj.fmt
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
def authenticate_begin(request):
    auth_data, state = SERVER.authenticate_begin(
        get_credentials(request.user)
    )
    request.session[SESSION_KEY] = state
    return HttpResponse(cbor.encode(auth_data), content_type="application/octet-stream")


@csrf_exempt
@login_required
def authenticate_complete(request):
    data = cbor.decode(request.body)

    cred = SERVER.authenticate_complete(
        state=request.session.pop(SESSION_KEY),
        credentials=get_credentials(request.user),
        credentials_id=data['credentialId'],
        client_data=ClientData(data['clientDataJSON']),
        auth_data=AuthenticatorData(data['authenticatorData']),
        signature=data['signature']
    )

    for key in UserKey.objects.filter(user=request.user, key_type=KEY_TYPE_FIDO2, enabled=1):
        if AttestedCredentialData(websafe_decode(key.properties["device"])).credential_id == cred.credential_id:
            write_session(request, key)
            res = login(request)
            return JsonResponse({'status': "OK", "redirect": res["location"]})

    return JsonResponse({'status': "err"})
