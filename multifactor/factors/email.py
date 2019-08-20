from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import send_mail

from random import randint
import logging

from ..models import UserKey, KEY_TYPE_EMAIL
from ..common import render, write_session, login


logger = logging.getLogger(__name__)


def send_email(request, secret):
    res = render(request, "multifactor/Email/email_body.txt", {
        "request": request,
        "user": request.user,
        'otp': secret
    })

    try:
        send_mail(
            subject='One Time Password',
            message=res.content.decode('utf-8'),
            from_email=settings.SERVER_EMAIL,
            recipient_list=[request.user.email],
            fail_silently=False
        )
        return True
    except Exception:
        logger.exception('Could not send email.')
        return False


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
        if not send_email(request, request.session["email_secret"]):
            messages.error(request, "Error sending email. Please try again.")

    return render(request, "multifactor/Email/add.html", {})


@login_required
def auth(request):
    try:
        key = UserKey.objects.get(user=request.user, key_type=KEY_TYPE_EMAIL)
    except UserKey.DoesNotExist:
        messages.error(request, "No existing email factor on account.")
        return redirect('multifactor:authenticate')

    if request.method == "POST":
        if request.session["email_secret"] == request.POST["otp"].strip():
            write_session(request, key)
            return login(request)
        messages.error(request, 'That key was not correct.')

    else:
        request.session["email_secret"] = str(randint(0, 100000))
        if not send_email(request, request.session["email_secret"]):
            messages.error(request, "Error sending email. Please try again.")

    return render(request, "multifactor/Email/check.html", {})
