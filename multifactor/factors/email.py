from django.template.context_processors import csrf
from django.shortcuts import redirect
from django.conf import settings
from django.utils import timezone

from random import randint

from ..models import UserKey, KEY_TYPE_EMAIL
from ..views import login
from ..common import send, next_check, render


def send_email(request, secret):
    res = render(request, "multifactor/Email/email_token_template.html", {
        "request": request,
        "user": request.user,
        'otp': secret
    })
    return send([request.user.email], "OTP", str(res.content))


def start(request):
    context = csrf(request)
    if request.method == "POST":
        if request.session["email_secret"] == request.POST["otp"]:
            UserKey.objects.create(
                user=request.user,
                key_type=KEY_TYPE_EMAIL,
                enabled=1,
            )
            return redirect('multifactor:home')
        context["invalid"] = True
    else:
        request.session["email_secret"] = str(randint(0, 100000))
        if send_email(request, request.session["email_secret"]):
            context["sent"] = True

    return render(request, "multifactor/Email/add.html", context)


def auth(request):
    context = csrf(request)
    if request.method == "POST":
        if request.session["email_secret"] == request.POST["otp"].strip():
            key = UserKey.objects.get(user=request.user, key_type=KEY_TYPE_EMAIL)

            mfa = {"verified": True, "method": "Email", "id": key.id}
            if getattr(settings, "MFA_RECHECK", False):
                mfa["next_check"] = next_check()
            request.session["multifactor"] = mfa

            key.last_used = timezone.now()
            key.save()

            return login(request)
        context["invalid"] = True
    else:
        request.session["email_secret"] = str(randint(0, 100000))
        if send_email(request, request.session["email_secret"]):
            context["sent"] = True

    return render(request, "multifactor/Email/check.html", {
        **context,
        'mode': 'auth'
    })
