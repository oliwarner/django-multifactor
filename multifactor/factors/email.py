from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from random import randint

from ..models import UserKey, KEY_TYPE_EMAIL
from ..views import login
from ..common import send, render, write_session


def send_email(request, secret):
    res = render(request, "multifactor/Email/email_token_template.html", {
        "request": request,
        "user": request.user,
        'otp': secret
    })
    return send([request.user.email], "OTP", str(res.content))


@login_required
def create(request):
    if request.method == "POST":
        if request.session["email_secret"] == request.POST["otp"]:
            key = UserKey.objects.create(
                user=request.user,
                key_type=KEY_TYPE_EMAIL,
                enabled=True,
            )
            write_session(request, key)
            messages.success(request, 'Success. Email authentication factor created.')
            return redirect('multifactor:home')
        messages.error(request, 'That key was not correct.')

    else:
        request.session["email_secret"] = str(randint(0, 100000))
        if send_email(request, request.session["email_secret"]):
            messages.info(request, 'Email sent.')

    return render(request, "multifactor/Email/add.html", {})


@login_required
def auth(request):
    if request.method == "POST":
        if request.session["email_secret"] == request.POST["otp"].strip():
            key = UserKey.objects.get(user=request.user, key_type=KEY_TYPE_EMAIL)
            write_session(request, key)
            return login(request)
        messages.error(request, 'That key was not correct.')

    else:
        request.session["email_secret"] = str(randint(0, 100000))
        if send_email(request, request.session["email_secret"]):
            messages.info(request, 'Email sent.')

    return render(request, "multifactor/Email/check.html", {})
