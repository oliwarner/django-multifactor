from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.shortcuts import render as dj_render

import random

from .app_settings import mf_settings


def send(to, subject, body):
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.SERVER_EMAIL,
        recipient_list=to,
        html_message=body,
        fail_silently=False
    )


def next_check():
    rando = random.randint(mf_settings['RECHECK_MIN'], mf_settings['RECHECK_MAX'])
    return int(timezone.now().strftime("%s")) + rando


def render(request, template_name, context, **kwargs):
    return dj_render(request, template_name, {
        **context
    }, **kwargs)

def method_url(method):
    return f'multifactor:{method.lower()}_auth'
