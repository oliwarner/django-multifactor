from django.shortcuts import redirect
from django.contrib.auth import get_user_model
from django.contrib import messages

import functools
import time

from .helpers import is_mfa, has_mfa_keys
from .common import method_url


__all__ = ['multifactor_protected']


def multifactor_protected(user_filter=None, force=False):
    def _func_wrapper(view_func, *args, **kwargs):
        @functools.wraps(view_func)
        def _wrapped_view_func(request, *args, **kwargs):
            def baulk():
                return view_func(request, *args, **kwargs)

            if not request.user.is_authenticated:
                return baulk()

            if user_filter is not None:
                # we're filtering for specific users
                if not get_user_model().objects.filter(pk=request.user.pk, **user_filter).exists():
                    return baulk()

            if has_mfa_keys(request):
                if not is_mfa(request):
                    request.session['multifactor-next'] = request.get_full_path()
                    return redirect('multifactor:authenticate')

                next_check = request.session.get('multifactor', {}).get('next_check', False)
                if next_check:
                    now = int(time.time())
                    if now >= next_check:
                        request.session['multifactor-next'] = request.get_full_path()
                        method = request.session['multifactor']['method']
                        return redirect(method_url(method))

            elif force:
                messages.info('Additional security factors are required to pass this view. Please add or enable at least one to continue.')
                request.session['multifactor-next'] = request.get_full_path()
                return redirect('multifactor:home')

            return baulk()
        return _wrapped_view_func
    return _func_wrapper
