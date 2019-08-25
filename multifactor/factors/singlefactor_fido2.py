from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt

from fido2 import cbor
from fido2.client import ClientData
from fido2.server import Fido2Server, RelyingParty, USER_VERIFICATION, WEBAUTHN_TYPE
from fido2.ctap2 import AttestationObject, AuthenticatorData
from fido2.utils import websafe_decode, websafe_encode
from fido2.ctap2 import AttestedCredentialData
from cryptography.hazmat.primitives import constant_time
from cryptography.exceptions import InvalidSignature
import logging
import os

from ..models import UserKey, KEY_TYPE_FIDO2
from ..common import render, write_session, login
from ..app_settings import mf_settings


class SinglefactorFido2Server(Fido2Server):

    def authenticate_begin(self):
        """
        Return a PublicKeyCredentialRequestOptions assertion object and
        the internal state dictionary that needs to be passed as is to the
        corresponding `authenticate_complete` call.

        :param user_verification: The desired USER_VERIFICATION level.
        :return: Assertion data, internal state.
        """
        uv = 'required'
        challenge = os.urandom(32)

        data = {
            'publicKey': {
                'rpId': self.rp.ident,
                'challenge': challenge,
                'timeout': int(self.timeout * 1000),
                'userVerification': uv
            }
        }

        state = self._make_internal_state(challenge, uv)

        return data, state

    def authenticate_complete(self, state, credential, client_data, auth_data, signature):
        """
        Verify the correctness of the assertion data received from the client.
        :param state: The state data returned by the corresponding `register_begin`.
        :param credential: The credential from the client response.
        :param client_data: The client data.
        :param auth_data: The authenticator data.
        :param signature: The signature provided by the client.
        """
        if client_data.get('type') != WEBAUTHN_TYPE.GET_ASSERTION:
            raise ValueError('Incorrect type in ClientData.')

        if not self._verify(client_data.get('origin')):
            raise ValueError('Invalid origin in ClientData.')

        if websafe_decode(state['challenge']) != client_data.challenge:
            raise ValueError('Wrong challenge in response.')

        if not constant_time.bytes_eq(self.rp.id_hash, auth_data.rp_id_hash):
            raise ValueError('Wrong RP ID hash in response.')

        if state['user_verification'] is USER_VERIFICATION.REQUIRED and \
                not auth_data.is_user_verified():
            raise ValueError(
                'User verification required, but user verified flag not set.')

        try:
            credential.public_key.verify(auth_data + client_data.hash, signature)
        except InvalidSignature:
            raise ValueError('Invalid signature.')
        return credential


SESSION_KEY = 'multifactor_fido_state'

SERVER = SinglefactorFido2Server(
    rp=RelyingParty(
        ident=mf_settings['FIDO_SERVER_ID'],
        name=mf_settings['FIDO_SERVER_NAME'],
        icon=mf_settings['FIDO_SERVER_ICON']
    )
)


def auth(request):
    return render(request, "multifactor/FIDO2/singlefactor_login.html", {})


def authenticate_begin(request):
    auth_data, request.session[SESSION_KEY] = SERVER.authenticate_begin()
    return HttpResponse(cbor.encode(auth_data), content_type="application/octet-stream")


@csrf_exempt
def authenticate_complete(request):
    data = cbor.decode(request.body)
    print(data)

    # todo find the credential NOW

    cred = SERVER.authenticate_complete(
        state=request.session.pop(SESSION_KEY),
        credential=data['credentialId'],
        client_data=ClientData(data['clientDataJSON']),
        auth_data=AuthenticatorData(data['authenticatorData']),
        signature=data['signature']
    )

    # TODO limit to login_enabled, and passes a user filter
    for key in UserKey.objects.filter(key_type=KEY_TYPE_FIDO2, enabled=1):
        if AttestedCredentialData(websafe_decode(key.properties["device"])).credential_id == cred.credential_id:
            write_session(request, key)
            res = login(request)
            return JsonResponse({'status': "OK", "redirect": res["location"]})

    return JsonResponse({'status': "err"})
