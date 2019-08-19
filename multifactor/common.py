from django.conf import settings
from django.utils import timezone
from django.shortcuts import render as dj_render, redirect

import random

from .app_settings import mf_settings
from .models import UserKey



def has_multifactor(request):
    return UserKey.objects.filter(user=request.user, enabled=True).exists()


def active_factors(request):
    # automatically expire old factors
    now = timezone.now().timestamp()
    factors = request.session["multifactor"] = [
        *filter(
            lambda tup: tup[3] > now,
            request.session.get('multifactor', [])
        ),
    ]
    return factors


def next_check():
    return timezone.now().timestamp() + random.randint(
        mf_settings['RECHECK_MIN'],
        mf_settings['RECHECK_MAX']
    )


def render(request, template_name, context, **kwargs):
    return dj_render(request, template_name, {
        **context
    }, **kwargs)


def method_url(method):
    return f'multifactor:{method.lower()}_auth'


def write_session(request, key):
    """Write the multifactor session with the verified key"""
    request.session["multifactor"] = [
        (
            key.key_type,
            key.id,
            timezone.now().timestamp(),
            next_check() if mf_settings["RECHECK"] else False
        ),
        *filter(
            lambda tup: tup[1] != key.id,
            request.session.get('multifactor', [])
        ),
    ]

    key.last_used = timezone.now()
    key.save()


def login(request):
    if 'multifactor-next' in request.session:
        return redirect(request.session['multifactor-next'])

    callback = mf_settings['LOGIN_CALLBACK']
    if callback:
        callable_func = import_string(callback)
        return callable_func(request, username=request.session["base_username"])

    # punch back to the login URL and let it decide what to do with you
    return redirect(settings.LOGIN_URL)
