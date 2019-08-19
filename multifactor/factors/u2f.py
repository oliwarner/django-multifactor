from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect

import json
import hashlib
from u2flib_server.u2f import (begin_registration, begin_authentication,
                               complete_registration, complete_authentication)
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import Encoding

from ..models import UserKey, KEY_TYPE_U2F
from ..common import render, write_session, login
from ..app_settings import mf_settings


@login_required
def start(request):
    if request.method == 'POST':
        device, cert = complete_registration(
            request.session['_u2f_enroll_'],
            json.loads(request.POST["response"]),
            [mf_settings['U2F_APPID']]
        )
        cert = x509.load_der_x509_certificate(cert, default_backend())
        cert_hash = hashlib.md5(cert.public_bytes(Encoding.PEM)).hexdigest()

        # if UserKey.objects.filter(key_type=KEY_TYPE_U2F, properties__icontains=cert_hash).exists():
        #     return HttpResponse("This key is registered before, it can't be registered again.")

        UserKey.objects.filter(user=request.user, key_type=KEY_TYPE_U2F).delete()
        key = UserKey.objects.create(
            user=request.user,
            properties={
                "device": json.loads(device.json),
                "cert": cert_hash,
            },
            key_type=KEY_TYPE_U2F,
        )
        write_session(request, key)
        messages.success(request, "U2F key added to account.")
        return redirect('multifactor:home')

    enroll = begin_registration(mf_settings['U2F_APPID'], [])
    request.session['_u2f_enroll_'] = enroll.json

    return render(request, "multifactor/U2F/add.html", {
        'token': json.dumps(enroll.data_for_client),
        'mode': 'auth',
    })


@login_required
def auth(request):
    if request.method == 'POST':
        data = json.loads(request.POST["response"])
        if data.get("errorCode", 0) != 0:
            messages.error(request, "Invalid security key response.")

        else:
            challenge = request.session.pop('_u2f_challenge_')
            device, c, t = complete_authentication(challenge, data, [mf_settings['U2F_APPID']])

            key = UserKey.objects.get(
                user=request.user,
                properties__device__publicKey=device["publicKey"]
            )
            write_session(request, key)
            return login(request)

    u2f_devices = [
        d.device
        for d in UserKey.objects.filter(user=request.user, key_type=KEY_TYPE_U2F)
    ]
    challenge = begin_authentication(mf_settings['U2F_APPID'], u2f_devices)
    request.session["_u2f_challenge_"] = challenge.json

    return render(request, "multifactor/U2F/check.html", {
        'token': json.dumps(challenge.data_for_client),
        'mode': 'auth',
    })
