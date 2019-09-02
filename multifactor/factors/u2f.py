from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

import json
import hashlib
from u2flib_server import u2f
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import Encoding

from ..models import UserKey, KEY_TYPE_U2F
from ..common import write_session, login
from ..app_settings import mf_settings


class BaseMixin:
    @property
    def base(self):
        return dict(
            user=self.request.user,
            key_type=KEY_TYPE_U2F,
            properties__domain=self.request.get_host()
        )


class Create(BaseMixin, LoginRequiredMixin, TemplateView):
    template_name = "multifactor/U2F/add.html"

    def get_context_data(self, **kwargs):
        enroll = u2f.begin_registration(mf_settings['U2F_APPID'], [])
        self.request.session['multifactor_u2f_enroll_'] = enroll.json
        return {
            'token': json.dumps(enroll.data_for_client),
        }

    def post(self, request, *args, **kwargs):
        if 'response' not in request.POST or any(x not in request.POST["response"] for x in ['clientData', 'registrationData', 'version']):
            messages.error(request, "Invalid U2F response, please try again.")
            return redirect('multifactor:home')

        device, cert = u2f.complete_registration(
            request.session['multifactor_u2f_enroll_'],
            json.loads(request.POST["response"]),
            [mf_settings['U2F_APPID']]
        )
        cert = x509.load_der_x509_certificate(cert, default_backend())
        cert_hash = hashlib.sha384(cert.public_bytes(Encoding.PEM)).hexdigest()

        if UserKey.objects.filter(**self.base, properties__cert=cert_hash).exists():
            messages.info(request, "That key's already in your account.")
            return redirect('multifactor:home')

        key = UserKey.objects.create(
            user=request.user,
            key_type=KEY_TYPE_U2F,
            properties={
                "device": json.loads(device.json),
                "cert": cert_hash,
                "domain": request.get_host(),
            },
        )
        write_session(request, key)
        messages.success(request, "U2F key added to account.")
        return redirect('multifactor:home')


class Auth(BaseMixin, LoginRequiredMixin, TemplateView):
    template_name = "multifactor/U2F/check.html"

    def dispatch(self, request, *args, **kwargs):
        self.keys = UserKey.objects.filter(
            **self.base,
            enabled=True
        )
        if not self.keys.exists():
            messages.error(request, 'You have no U2F devices for this domain.')
            return redirect('multifactor:home')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        challenge = u2f.begin_authentication(
            mf_settings['U2F_APPID'],
            list(self.keys.values_list("properties__device", flat=True))
        )

        self.request.session["_u2f_challenge_"] = challenge.json

        return {
            'token': json.dumps(challenge.data_for_client),
        }

    def post(self, request, *args, **kwargs):
        data = json.loads(request.POST["response"])
        if data.get("errorCode", 0) != 0:
            messages.error(request, "Invalid security key response.")
            return super().get(request, *args, **kwargs)

        challenge = request.session.pop('_u2f_challenge_')
        device, c, t = u2f.complete_authentication(challenge, data, [mf_settings['U2F_APPID']])

        key = self.keys.get(properties__device__publicKey=device["publicKey"])
        write_session(request, key)
        return login(request)
