from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import send_mail
from django.utils.module_loading import import_string
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from random import randint
import logging

from ..common import render, write_session, login, disabled_fallbacks
from ..app_settings import mf_settings


logger = logging.getLogger(__name__)

SESSION_KEY = 'multifactor-fallback-otp'


class Auth(LoginRequiredMixin, TemplateView):
    template_name = "multifactor/fallback/auth.html"
    succeeded = []

    def get(self, request):
        otp = request.session[SESSION_KEY] = request.session.get(SESSION_KEY, str(randint(0, 100000000)))
        message = f'Dear {request.user.get_full_name()},\nYour one-time-password is: {otp}'

        disabled = disabled_fallbacks(request)
        s = []
        for name, (field, method) in mf_settings['FALLBACKS'].items():
            if name in disabled or not field(request.user):
                continue

            try:
                imported_method = import_string(method)
                if imported_method(request.user, message):
                    s.append(name)
            except:
                pass

        if not s:
            messages.error(request, 'No fallback OTP transport methods worked. Please contact an administrator.')
            return redirect('multifactor:home')

        self.succeeded = s[0] if len(s) == 1 else (', '.join(s[:-1]) + ' and ' + s[-1])
        return super().get(request)

    def get_context_data(self, **kwargs):
        return {
            'succeeded': self.succeeded,
        }

    def post(self, request):
        if request.session[SESSION_KEY] == request.POST["otp"].strip():
            request.session.pop(SESSION_KEY)
            write_session(request, key=None)
            return login(request)

        self.succeeded = request.POST.get("succeeded")
        messages.error(request, 'That key was not correct. Please try again.')
        return super(TemplateView, self).get(request)


def send_email(user, message):
    try:
        send_mail(
            subject='One Time Password',
            message=message,
            from_email=settings.SERVER_EMAIL,
            recipient_list=[user.email],
            fail_silently=False
        )
        return True
    except Exception:
        logger.exception('Could not send email.')
        return False
