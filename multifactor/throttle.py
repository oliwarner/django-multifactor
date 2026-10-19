"""Attempt logging and lockout for one-time-code factors (TOTP and fallback OTP).

Every attempt is stored as an `AuthAttempt`. Lockout is derived from those rows, not kept as
separate state: a user is locked when their most recent `MAX_ATTEMPTS` failures since their
last success all fall within `ATTEMPT_PERIOD` seconds of each other, and stays locked until
`LOCKOUT_PERIOD` seconds after the latest of them. One log is shared by every OTP factor, so
alternating between TOTP and the fallback route doesn't multiply the guesses available.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.db import transaction
from django.db.models import Max
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import gettext as _

from .app_settings import mf_settings
from .models import AuthAttempt

logger = logging.getLogger(__name__)

Outcomes = AuthAttempt.Outcomes


def locked_until(user):
    """When the user's lockout ends, or None if they aren't locked out."""
    limit = mf_settings["MAX_ATTEMPTS"]
    if not limit:
        return None

    attempts = AuthAttempt.objects.filter(user=user)
    last_success = attempts.filter(outcome=Outcomes.SUCCESS).aggregate(t=Max("timestamp"))["t"]
    failures = attempts.filter(outcome=Outcomes.FAILURE)
    if last_success:
        failures = failures.filter(timestamp__gt=last_success)

    recent = list(failures.order_by("-timestamp").values_list("timestamp", flat=True)[:limit])
    if len(recent) < limit:
        return None

    if recent[0] - recent[-1] > timedelta(seconds=mf_settings["ATTEMPT_PERIOD"]):
        return None

    until = recent[0] + timedelta(seconds=mf_settings["LOCKOUT_PERIOD"])
    return until if until > timezone.now() else None


def is_locked(user):
    return locked_until(user) is not None


def begin_attempt(user, factor):
    """Reserve an attempt before the code is checked.

    Returns an `AuthAttempt` (recorded as a failure until `succeed()` is called), or None if
    the user is locked out, in which case a `blocked` row is written instead. The user's row
    is locked while checking and reserving so that a burst of parallel requests can't all pass
    the lockout check before any of them has been counted.
    """
    if not mf_settings["MAX_ATTEMPTS"]:
        return AuthAttempt(user=user, factor=factor)  # unsaved: nothing is logged or limited

    with transaction.atomic():
        get_user_model()._default_manager.select_for_update().get(pk=user.pk)
        if is_locked(user):
            AuthAttempt.objects.create(user=user, factor=factor, outcome=Outcomes.BLOCKED)
            return None

        return AuthAttempt.objects.create(user=user, factor=factor, outcome=Outcomes.FAILURE)


def succeed(attempt):
    attempt.outcome = Outcomes.SUCCESS
    if attempt.pk:
        attempt.save(update_fields=["outcome"])


def lock_out(request):
    """Log the user out and send them back to the login page."""
    logger.warning(
        "Multifactor OTP attempt limit reached for user pk=%s; logging out.",
        request.user.pk,
    )
    logout(request)
    messages.error(request, _("Too many failed attempts. Please try again later."))
    return redirect(settings.LOGIN_URL)


def prune(days=None):
    """Delete attempts older than `days` (default ATTEMPT_RETENTION_DAYS). Returns the count."""
    days = mf_settings["ATTEMPT_RETENTION_DAYS"] if days is None else days
    deleted, _ = AuthAttempt.objects.filter(timestamp__lt=timezone.now() - timedelta(days=days)).delete()
    return deleted
