# django-multifactor

A Django app that handles multifactor authentication. It supports TOTP, U2F, FIDO2 U2F (WebAuthn), Email Tokens as well as custom handlers for OTP token exchange (eg SMS plugins). This project is based on [`django-mfa2`](https://pypi.org/project/django-mfa2/), but has and will continue to diverge from it, and eventually become a complete rewrite.

[![PyPI version](https://badge.fury.io/py/django-multifactor.svg)](https://badge.fury.io/py/django-multifactor)

FIDO2/WebAuthn is the big-ticket item for MFA. It allows the browser to interface with a myriad of biometric and secondary authentication factors.

 * **Security keys** (Firefox 60+, Chrome 67+, Edge 18+),
 * **Windows Hello** (Firefox 67+, Chrome 72+ , Edge) ,
 * **Apple's Touch ID** (Chrome 70+ on Mac OS X ),
 * **android-safetynet** (Chrome 70+)
 * **NFC devices using PCSC** (Not Tested, but as supported in fido2)

This project targets modern stacks of Django 2.2+ and Python 3.5+.


## Installation:

Install the package:

    pip install django-multifactor

Add `multifactor` to your settings.INSTALLED_APPS.

Add and customise the following settings block:

    MULTIFACTOR = {
        'LOGIN_CALLBACK': False,             # False, or dotted import path to function to process after successful authentication
        'RECHECK': True,                     # Invalidate previous authorisations at random intervals
        'RECHECK_MIN': 60 * 60 * 3,          # No recheks before 3 hours
        'RECHECK_MAX': 60 * 60 * 6,          # But within 6 hours
    
        'FIDO_SERVER_ID': 'example.com',     # Server ID for FIDO request
        'FIDO_SERVER_NAME': 'Django App',    # Human-readable name for FIDO request
        'TOKEN_ISSUER_NAME': 'Django App',   # TOTP token issuing name (to be shown in authenticator)
        'U2F_APPID': 'https://example.com',  # U2F request issuer
    }

Add the multifactor to your URLs. I suggest somewhere similar to your login URLs, or underneath them, eg:

    urlpatterns = [
        path('admin/multifactor/', include('multifactor.urls')),
        path('admin/', admin.site.urls),
        ...
    ]


## Usage

By this point any authenticated user can add a secondary factor to their account by visiting (eg) `/admin/multifactor/`, but no view will *require* users be multi-factor authenticated. django-multifactor give you granular control to conditionally require certain users need a secondary factor on certain views. This is accomplished through the `multifactor.decorators.multifactor_protected` decorator.

from multifactor.decorators import multifactor_protected

    @multifactor_protected(user_filter=None, force=False)
    def my_view(request):
        ...

 - `user_filter` can be a dictonary to be passed to `User.objects.filter()` to see if the current user matches these conditions. If empty or None, it will match all users.
 - `force=True` would force a user (who matched `user_filter`) to add a secondary factor and authenticate. If `force=False`, users who have not yet added a multifactor token will be allowed unimpeded.

 You can also wrap entire branches of your URLs using [`django-decorator-include`](https://pypi.org/project/django-decorator-include/):

    from decorator_include import decorator_include
    from multifactor.decorators import multifactor_protected

    urlpatterns = [
        path('admin/multifactor/', include('multifactor.urls')),
        path('admin/', decorator_include(multifactor_protected(force=True), admin.site.urls)),
        ...
    ]


## TODO

 - Allow custom handlers for simple OTP sending.
 - Allow settings to limit what can be added.
 - Allow `multifactor_protected` to require more than one secondary factor.