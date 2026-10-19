"""Failed-attempt counting for one-time-code factors (TOTP and fallback OTP).

Counters are keyed on the user and shared between every OTP factor, so an attacker can't
multiply their guesses by alternating between TOTP and the fallback route. They are stored in
Django's cache; use a cache shared between all workers in production.
"""

import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.core.cache import cache
from django.shortcuts import redirect
from django.utils.translation import gettext as _

from .app_settings import mf_settings

logger = logging.getLogger(__name__)


def _cache_key(user):
    return f"multifactor-failed-otp:{user.pk}"


def is_locked(user):
    limit = mf_settings["MAX_ATTEMPTS"]
    return bool(limit) and cache.get(_cache_key(user), 0) >= limit


def record_failure(user):
    """Count a failed attempt. Returns True if the user has now reached the limit."""
    limit = mf_settings["MAX_ATTEMPTS"]
    if not limit:
        return False

    key = _cache_key(user)
    cache.add(key, 0, mf_settings["ATTEMPT_PERIOD"])
    try:
        count = cache.incr(key)
    except ValueError:  # expired between add and incr
        cache.set(key, 1, mf_settings["ATTEMPT_PERIOD"])
        count = 1

    return count >= limit


def reset(user):
    cache.delete(_cache_key(user))


def lock_out(request):
    """Log the user out and send them back to the login page."""
    logger.warning(
        "Multifactor OTP attempt limit reached for user pk=%s; logging out.",
        request.user.pk,
    )
    logout(request)
    messages.error(request, _("Too many failed attempts. Please try again later."))

    return redirect(settings.LOGIN_URL)
