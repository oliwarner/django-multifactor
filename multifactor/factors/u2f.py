from django.template.context_processors import csrf
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

import json
import hashlib
from u2flib_server.u2f import (begin_registration, begin_authentication,
                               complete_registration, complete_authentication)
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import Encoding

from ..models import UserKey, KEY_TYPE_U2F
from ..views import login
from ..common import next_check, render
from ..app_settings import mf_settings


def recheck(request):
    s = sign(request)

    request.session["_u2f_challenge_"] = s[0]
    request.session["mfa_recheck"] = True

    return render(request, "multifactor/U2F/check.html", {
        **csrf(request),
        "mode": "recheck",
        "token": s[1],
    })


def process_recheck(request):
    x = validate(request)
    if x is True:
        return JsonResponse({"recheck": True})
    return x


def check_errors(request, data):
    if data.get("errorCode", 0) == 0:
        return True

    if data["errorCode"] == 4:
        return HttpResponse("Invalid Security Key")

    if data["errorCode"] == 1:
        return auth(request)


def validate(request):
    data = json.loads(request.POST["response"])

    res = check_errors(request, data)
    if res is not True:
        return res

    challenge = request.session.pop('_u2f_challenge_')
    device, c, t = complete_authentication(challenge, data, [mf_settings['U2F_APPID']])

    key = UserKey.objects.get(
        user=request.user,
        properties__device__publicKey=device["publicKey"]
    )

    key.last_used = timezone.now()
    key.save()

    mfa = {
        "verified": True,
        "method": "U2F",
        "id": key.id
    }

    if mf_settings["RECHECK"]:
        mfa["next_check"] = next_check()

    request.session["multifactor"] = mfa
    return True


def auth(request):
    s = sign(request)
    request.session["_u2f_challenge_"] = s[0]

    return render(request, "multifactor/U2F/check.html", {
        **csrf(request),
        'token': s[1],
        'mode': 'auth',
    })


def start(request):
    enroll = begin_registration(mf_settings['U2F_APPID'], [])
    request.session['_u2f_enroll_'] = enroll.json

    return render(request, "multifactor/U2F/add.html", {
        **csrf(request),
        'token': json.dumps(enroll.data_for_client),
        'mode': 'auth',
    })


def bind(request):
    enroll = request.session['_u2f_enroll_']
    data = json.loads(request.POST["response"])
    device, cert = complete_registration(enroll, data, [mf_settings['U2F_APPID']])
    cert = x509.load_der_x509_certificate(cert, default_backend())
    cert_hash = hashlib.md5(cert.public_bytes(Encoding.PEM)).hexdigest()

    # if UserKey.objects.filter(key_type=KEY_TYPE_U2F, properties__icontains=cert_hash).exists():
    #     return HttpResponse("This key is registered before, it can't be registered again.")

    UserKey.objects.filter(user=request.user, key_type=KEY_TYPE_U2F).delete()
    UserKey.objects.create(
        user=request.user,
        properties={
            "device": json.loads(device.json),
            "cert": cert_hash,
        },
        key_type=KEY_TYPE_U2F,
    )
    return HttpResponse("OK")


def sign(request):
    u2f_devices = [
        d.device
        for d in UserKey.objects.filter(user=request.user, key_type=KEY_TYPE_U2F)
    ]

    challenge = begin_authentication(mf_settings['U2F_APPID'], u2f_devices)
    return [challenge.json, json.dumps(challenge.data_for_client)]


def verify(request):
    x = validate(request)
    if x is True:
        return login(request)
    return x
