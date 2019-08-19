from django.conf import settings
from django.utils import timezone
from django.shortcuts import render as dj_render, redirect

import random

from .app_settings import mf_settings


def next_check():
    return int(timezone.now().strftime("%s")) + random.randint(
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

    multifactor = {
        "verified": True,
        "method": key.key_type,
        "id": key.id,
    }

    if mf_settings["RECHECK"]:
        multifactor["next_check"] = next_check()

    request.session["multifactor"] = multifactor

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
