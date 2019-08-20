from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import send_mail
from django.utils.module_loading import import_string
from django.shortcuts import redirect

from random import randint
import logging

from ..common import render, write_session, login, get_profile
from ..app_settings import mf_settings


logger = logging.getLogger(__name__)

SESSION_KEY = 'multifactor-fallback-otp'


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


@login_required
def auth(request):
    profile = get_profile(request)
    # TODO check profile to see if we're allowed to do this
    fallbacks = {
        k: v
        for k, v in mf_settings['FALLBACKS'].items()
        if k not in profile.disabled_fallbacks and v[0](request.user)
    }

    if request.method == "POST":
        succeeded = request.POST.get("succeeded")
        if request.session[SESSION_KEY] == request.POST["otp"].strip():
            write_session(request, key=None)
            return login(request)
        messages.error(request, 'That key was not correct. Please try again.')

    else:
        otp = request.session[SESSION_KEY] = request.session.get(SESSION_KEY, str(randint(0, 100000000)))
        message = f'Dear {request.user.get_full_name()},\nYour one-time-password is: {otp}'

        succeeded = []
        for name, (field, method) in fallbacks.items():
            try:
                imported_method = import_string(method)
                if imported_method(request.user, message):
                    succeeded.append(name)
            except:
                logger.exception('Fallback exploded')
                pass

        if not succeeded:
            messages.error(request, 'No fallback OTP transport methods worked. Please contact an administrator.')
            # return redirect('multifactor:home')

        elif len(succeeded) == 1:
            succeeded = succeeded[0]

        else:
            succeeded = ', '.join(succeeded[:-1]) + ' and ' + succeeded[-1]

    return render(request, "multifactor/fallback/auth.html", {
        'succeeded': succeeded
    })
