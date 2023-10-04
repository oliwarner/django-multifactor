from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt

from fido2.server import Fido2Server
from fido2.webauthn import AttestedCredentialData, PublicKeyCredentialUserEntity
from fido2.utils import websafe_decode, websafe_encode
import fido2.features
import logging

from ..models import UserKey, KeyTypes
from ..common import write_session, login
from ..app_settings import mf_settings

import json

fido2.features.webauthn_json_mapping.enabled = True

logger = logging.getLogger(__name__)


def get_server():
    return Fido2Server(rp=dict(
        id=mf_settings['FIDO_SERVER_ID'],
        name=mf_settings['FIDO_SERVER_NAME']
    ))


@login_required
def begin_registration(request):
    server = get_server()
    registration_data, state = server.register_begin(
        user=PublicKeyCredentialUserEntity(
            id=request.user.get_username().encode('utf-8'),
            name=f'{request.user.get_full_name()}',
            display_name=request.user.get_username(),
        ),
        credentials=get_user_credentials(request),
    )
    request.session['fido_state'] = state

    return JsonResponse({**registration_data}, safe=False)


@csrf_exempt
@login_required
def complete_reg(request):
    try:
        server = get_server()
        data = json.loads(request.body)
        auth_data = server.register_complete(
            request.session['fido_state'], data)

        encoded = websafe_encode(auth_data.credential_data)
        key = UserKey.objects.create(
            user=request.user,
            properties={
                "device": encoded,
                "type": data['type'],
                "domain": server.rp.id,
            },
            key_type=KeyTypes.FIDO2,
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


def get_user_credentials(request):
    if not request.user.is_authenticated:
        return []
    return [
        AttestedCredentialData(websafe_decode(key.properties["device"]))
        for key in UserKey.objects.filter(
            user=request.user,
            key_type=KeyTypes.FIDO2,
            properties__domain=request.get_host(),
            enabled=True,
        )
    ]


@csrf_exempt
@login_required
def authenticate_begin(request):
    server = get_server()
    auth_data, state = server.authenticate_begin(
        credentials=get_user_credentials(request),
        user_verification="discouraged",
    )
    request.session['fido_state'] = state
    return JsonResponse({**auth_data})


@csrf_exempt
@login_required
def authenticate_complete(request):
    data = json.loads(request.body)

    cred = get_server().authenticate_complete(
        request.session.pop('fido_state'),
        get_user_credentials(request),
        data
    )

    keys = UserKey.objects.filter(
        user=request.user,
        key_type=KeyTypes.FIDO2,
        enabled=True,
    )

    for key in keys:
        if AttestedCredentialData(websafe_decode(key.properties["device"])).credential_id == cred.credential_id:
            write_session(request, key)
            res = login(request)
            return JsonResponse({'status': "OK", "redirect": res["location"]})

    return JsonResponse({'status': "err"})
