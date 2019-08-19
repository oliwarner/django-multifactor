from django.shortcuts import redirect
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse

import functools
import time
import inspect

from .common import method_url, active_factors, has_multifactor


__all__ = ['multifactor_protected']


def multifactor_protected(factors=0, user_filter=None, max_age=0, advertise=False):
    """
    Protect a view with multifactor authentication.

    Parameters
    ----------
    factors : int, function
        Number of separate factors that must be currently activated.
        You can also pass in a function accepting the request to return this number.
    user_filter : None | dict
        User-class.objects.filter dictionary to try to match current user.
    max_age : int
        Number of seconds since last authentication this view requires.
        Zero means infinite (or until it expires)
    advertise : bool
        Advertise to the user that they can optionally add keys for factors=0 views.
    """
    def _func_wrapper(view_func, *args, **kwargs):
        @functools.wraps(view_func)
        def _wrapped_view_func(request, *args, **kwargs):
            def baulk():
                return view_func(request, *args, **kwargs)

            if not request.user.is_authenticated:
                return baulk()

            if user_filter is not None:
                # we're filtering for specific users, check that the current user fits that
                if not get_user_model().objects.filter(pk=request.user.pk, **user_filter).exists():
                    return baulk()

            active = active_factors(request)

            if has_multifactor(request):
                if not active:
                    # has keys but isn't using them, tell them to authenticate
                    request.session['multifactor-next'] = request.get_full_path()
                    return redirect('multifactor:authenticate')

                elif max_age and active[0][3] + max_age < timezone.now().timestamp():
                    # has authenticated but not recently enough for this view
                    messages.warning(
                        request,
                        f'This page requires secondary authentication every {max_age} seconds. '
                        'Please re-authenticate.'
                    )
                    request.session['multifactor-next'] = request.get_full_path()
                    return redirect('multifactor:authenticate')

            required_factors = factors
            if inspect.isfunction(factors):
                required_factors = factors(request)

            if required_factors > len(active):
                # view needs more active factors than provided
                messages.warning(
                    request,
                    f'This page requires {required_factors} active security '
                    f'factor{"" if required_factors == 1 else "s"}.'
                )
                request.session['multifactor-next'] = request.get_full_path()
                return redirect('multifactor:home')

            if not active and advertise and 'multifactor-advertised' not in request.session:
                # tell them that they can add keys but it's entirely optional
                messages.info(request, format_html(
                    'Consider <a href="{}" class="alert-link">adding a second security factor</a> such as '
                    'a USB Security Token, or an Authenticator App on your phone. '
                    'This further protects your account and the data it can access.',
                    reverse('multifactor:home')
                ))
                request.session['multifactor-advertised'] = True

            return baulk()
        return _wrapped_view_func
    return _func_wrapper
