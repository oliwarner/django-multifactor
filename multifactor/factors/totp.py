from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

import pyotp

from ..models import UserKey, KEY_TYPE_TOPT
from ..common import render, write_session, login
from ..app_settings import mf_settings


@login_required
def create(request):
    """Create new key."""
    secret_key = request.POST.get("key", pyotp.random_base32())

    if request.method == "POST":
        answer = request.POST["answer"]
        totp = pyotp.TOTP(secret_key)

        if totp.verify(answer, valid_window=60):
            key = UserKey.objects.create(
                user=request.user,
                properties={"secret_key": secret_key},
                key_type=KEY_TYPE_TOPT
            )
            write_session(request, key)
            messages.success(request, 'Authenticator added.')
            return redirect("multifactor:home")

        messages.error(request, 'Could not validate key, please try again.')

    totp = pyotp.TOTP(secret_key)

    return render(request, "multifactor/TOTP/add.html", {
        "qr": totp.provisioning_uri(
            request.user.get_username(),
            issuer_name=mf_settings['TOKEN_ISSUER_NAME']
        ),
        "secret_key": secret_key,
    })


@login_required
def auth(request):
    def verify_login(request, token):
        for key in UserKey.objects.filter(user=request.user, key_type="TOTP"):
            if pyotp.TOTP(key.properties["secret_key"]).verify(token, valid_window=60):
                return True, key
        return False, None

    if request.method == "POST":
        success, key = verify_login(request, token=request.POST["answer"])
        if success:
            write_session(request, key)
            return login(request)

        messages.error(request, 'Could not validate key, please try again.')

    return render(request, "multifactor/TOTP/check.html", {})
