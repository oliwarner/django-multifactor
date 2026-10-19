import time

import pyotp
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import redirect
from django.utils.translation import gettext as _
from django.views.generic import TemplateView
from pyotp.utils import strings_equal

from ..app_settings import mf_settings
from ..common import login, write_session
from ..mixins import PreferMultiAuthMixin
from ..models import KeyTypes, UserKey
from ..throttle import begin_attempt, is_locked, lock_out, succeed


def matching_step(totp, token, last_step=None):
    """Return the time step `token` is valid for, or None.

    Only steps within TOTP_WINDOW of now are considered, and any step at or before
    `last_step` (the last one accepted for this key) is rejected so a code can't be replayed.
    """
    token = str(token).strip()
    window = mf_settings["TOTP_WINDOW"]
    current = int(time.time() // totp.interval)
    for step in range(current - window, current + window + 1):
        if last_step is not None and step <= last_step:
            continue

        if strings_equal(token, totp.generate_otp(step)):
            return step


class Create(PreferMultiAuthMixin, TemplateView):
    template_name = "multifactor/TOTP/add.html"

    def dispatch(self, request, *args, **kwargs):
        self.secret_key = request.POST.get("key", pyotp.random_base32())
        self.totp = pyotp.TOTP(self.secret_key)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "qr": self.totp.provisioning_uri(
                self.request.user.get_username(), issuer_name=mf_settings["TOKEN_ISSUER_NAME"]
            ),
            "secret_key": self.secret_key,
        }

    def post(self, request, *args, **kwargs):
        step = matching_step(self.totp, request.POST.get("answer", ""))
        if step is not None:
            key = UserKey.objects.create(
                user=request.user,
                properties={"secret_key": self.secret_key, "last_step": step},
                key_type=str(KeyTypes.TOTP),
            )
            write_session(request, key)
            messages.success(request, _("TOTP Authenticator added."))
            return redirect("multifactor:home")

        messages.error(request, _("Could not validate key, please try again."))
        return super().get(request, *args, **kwargs)


class Auth(LoginRequiredMixin, TemplateView):
    template_name = "multifactor/TOTP/check.html"

    def post(self, request, *args, **kwargs):
        attempt = begin_attempt(request.user, str(KeyTypes.TOTP))
        if attempt is None:
            return lock_out(request)

        key = self.verify_login(token=request.POST.get("answer", ""))
        if key:
            succeed(attempt)
            write_session(request, key)
            return login(request)

        if is_locked(request.user):  # this failure was the one that tripped the limit
            return lock_out(request)

        messages.error(request, _("Could not validate key, please try again."))
        return super().get(request, *args, **kwargs)

    def verify_login(self, token):
        with transaction.atomic():
            keys = UserKey.objects.select_for_update().filter(
                user=self.request.user, key_type=str(KeyTypes.TOTP), enabled=True
            )
            for key in keys:
                totp = pyotp.TOTP(key.properties["secret_key"])
                step = matching_step(totp, token, key.properties.get("last_step"))
                if step is not None:
                    key.properties["last_step"] = step
                    key.save(update_fields=["properties"])
                    return key
