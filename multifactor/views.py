from django.shortcuts import redirect
from django.http import HttpResponse, Http404
from django.conf import settings
from django.utils.module_loading import import_string
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.html import format_html
from django.urls import reverse

from .models import UserKey, DisabledFallback, KEY_CHOICES
from .common import render, method_url, active_factors, has_multifactor, disabled_fallbacks
from .app_settings import mf_settings
from .decorators import multifactor_protected


@login_required
def index(request):
    authed = active_factors(request)
    methods = [
        (f"multifactor:{value.lower()}_start", label)
        for value, label in KEY_CHOICES
    ]

    can_edit = not has_multifactor(request) or bool(authed)

    if not can_edit:
        messages.warning(request, format_html(
            'You will not be able to change these settings or add new '
            'factors until until you <a href="{}" class="alert-link">authenticate</a> with '
            'one of your existing secondary factors.',
            reverse('multifactor:authenticate')
        ))

    disabled = disabled_fallbacks(request)
    available_fallbacks = [
        (k, k not in disabled, v[0](request.user))
        for k, v in mf_settings['FALLBACKS'].items()
        if v[0](request.user)
    ]

    return render(request, "multifactor/home.html", {
        "keys": UserKey.objects.filter(user=request.user),
        'authed_kids': [k[1] for k in authed],
        "available_methods": methods,
        "can_edit": can_edit,
        'available_fallbacks': available_fallbacks,
    })


@login_required
def verify(request):
    factors = UserKey.objects.filter(user=request.user, enabled=True)

    if not factors:
        messages.warning(request, 'You have not set up your factors. Please add one (or more).')
        return redirect('multifactor:home')

    methods = list(set([k.key_type for k in factors]))

    disabled = disabled_fallbacks(request)
    available_fallbacks = [
        k for k, v in mf_settings['FALLBACKS'].items()
        if k not in disabled and v[0](request.user)
    ]

    if len(methods) == 1 and not available_fallbacks:
        return redirect(method_url(methods[0]))

    method_names = dict(KEY_CHOICES)

    return render(request, 'multifactor/verify.html', {
        'methods': [
            (method_url(method), method_names[method])
            for method in methods
        ],
        'fallbacks': available_fallbacks,
    })


@login_required
def reset_cookie(request):
    del request.session['multifactor']
    return redirect(settings.LOGIN_URL)


@login_required
@multifactor_protected(max_age=600)
def delete_factor(request):
    if not request.POST.get('kid'):
        raise Http404()

    try:
        key = UserKey.objects.get(user=request.user, pk=request.POST['kid'])
        key.delete()
        messages.info(request, f'{key.get_key_type_display()} has been deleted.')

    except UserKey.DoesNotExist:
        messages.error(request, f'{key.get_key_type_display()} not found.')

    return redirect('multifactor:home')


@login_required
@multifactor_protected(max_age=600)
def toggle_factor(request):
    if not request.POST.get('kid'):
        raise Http404()

    try:
        key = UserKey.objects.get(user=request.user, pk=request.POST['kid'])
        key.enabled = not key.enabled
        key.save()
        messages.info(request, f'{key.get_key_type_display()} has been {"enabled" if key.enabled else "disabled"}.')

    except UserKey.DoesNotExist:
        messages.error(request, f'{key.get_key_type_display()} not found.')

    return redirect('multifactor:home')


@login_required
@multifactor_protected(max_age=600)
def toggle_fallback(request):
    fallback = request.POST.get('fallback')
    if fallback and fallback in mf_settings['FALLBACKS']:
        n, _ = DisabledFallback.objects.filter(user=request.user, fallback=fallback).delete()
        if n:  # managed to delete something
            messages.info(request, f"{fallback} fallback factor has been re-enabled.")

        else:  # didn't so creating new block
            messages.info(request, f"{fallback} fallback factor has been disabled.")
            DisabledFallback(user=request.user, fallback=fallback).save()

    return redirect('multifactor:home')
