from django.http import JsonResponse, HttpResponse
from django.template.context_processors import csrf
from django.utils import timezone

import pyotp

from ..models import UserKey, KEY_TYPE_TOPT
from ..views import login
from ..common import next_check, render
from ..app_settings import mf_settings


def verify_login(request, token):
    for key in UserKey.objects.filter(user=request.user, key_type="TOTP"):
        if pyotp.TOTP(key.properties["secret_key"]).verify(token, valid_window=30):
            key.last_used = timezone.now()
            key.save()
            return [True, key.id]
    return [False]


def recheck(request):
    context = csrf(request)
    context["mode"] = "recheck"
    if request.method == "POST":
        if verify_login(request, token=request.POST["otp"]):
            return JsonResponse({"recheck": True})
        else:
            return JsonResponse({"recheck": False})
    return render(request, "multifactor/TOTP/check.html", context)


def auth(request):
    context = csrf(request)
    if request.method == "POST":
        res = verify_login(request, token=request.POST["otp"])
        if res[0]:
            mfa = {"verified": True, "method": "TOTP", "id": res[1]}
            if mf_settings["RECHECK"]:
                mfa["next_check"] = next_check()
            request.session["mfa"] = mfa
            return login(request)
        context["invalid"] = True
    return render(request, "multifactor/TOTP/check.html", context)


def get_token(request):
    secret_key = pyotp.random_base32()
    totp = pyotp.TOTP(secret_key)
    request.session["new_mfa_answer"] = totp.now()
    return JsonResponse({
        "qr": totp.provisioning_uri(
            request.user.get_username(),
            issuer_name=mf_settings['TOKEN_ISSUER_NAME']
        ),
        "secret_key": secret_key
    })


def verify(request):
    answer = request.GET["answer"]
    secret_key = request.GET["key"]
    totp = pyotp.TOTP(secret_key)

    if not totp.verify(answer, valid_window=60):
        return HttpResponse("Error")

    UserKey.objects.create(
        user=request.user,
        properties={"secret_key": secret_key},
        key_type=KEY_TYPE_TOPT
    )
    return HttpResponse("Success")


def start(request):
    return render(request, "multifactor/TOTP/add.html", {})
