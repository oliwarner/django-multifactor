![](https://raw.githubusercontent.com/oliwarner/django-multifactor/master/logo.png)

###Easy multi-factor authentication for Django

Supports TOTP, U2F, FIDO2 U2F (WebAuthn), Email Tokens as well as custom handlers for OTP token exchange (eg SMS plugins).  
This is ***not*** a passwordless authentication system, rather adding to your existing authentication format.

Based on [`django-mfa2`](https://pypi.org/project/django-mfa2/) but quickly diverging.

[![PyPI version](https://badge.fury.io/py/django-multifactor.svg)](https://badge.fury.io/py/django-multifactor)

FIDO2/WebAuthn is the big-ticket item for MFA. It allows the browser to interface with a myriad of biometric and secondary authentication factors.

 * **Security keys** (Firefox 60+, Chrome 67+, Edge 18+),
 * **Windows Hello** (Firefox 67+, Chrome 72+ , Edge) ,
 * **Apple's Touch ID** (Chrome 70+ on Mac OS X ),
 * **android-safetynet** (Chrome 70+)
 * **NFC devices using PCSC** (Not Tested, but as supported in fido2)

This project targets modern stacks. Django 2.2+ and Python 3.5+.


## Installation:

Install the package:

    pip install django-multifactor

Add `multifactor` to `settings.INSTALLED_APPS`.

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

Ensure that [`django.contrib.messages`](https://docs.djangoproject.com/en/2.2/ref/contrib/messages/) is installed.

Include `multifactor.urls` in your URLs. You can do this anywhere but I suggest somewhere similar to your login URLs, or underneath them, eg:

    urlpatterns = [
        path('admin/multifactor/', include('multifactor.urls')),
        path('admin/', admin.site.urls),
        ...
    ]


## Usage

At this stage any authenticated user can add a secondary factor to their account by visiting (eg) `/admin/multifactor/`, but no view will *require* secondary authentication. django-multifactor gives you granular control to conditionally require certain users need a secondary factor on certain views. This is accomplished through the `multifactor.decorators.multifactor_protected` decorator.

    from multifactor.decorators import multifactor_protected

    @multifactor_protected(factors=0, user_filter=None, max_age=0, advertise=False)
    def my_view(request):
        ...

 - `factors` is the minimum number of active, authenticated secondary factors. 0 will mean users will only be prompted if they have keys. It can also accept a lambda/function with one request argument that returns a number. This allows you to tune whether factors are required based on custom logic (eg if local IP return 0 else return 1)
 - `user_filter` can be a dictonary to be passed to `User.objects.filter()` to see if the current user matches these conditions. If empty or None, it will match all users.
 - `max_age=600` will ensure the the user has authenticated with their secondary factor within 10 minutes. You can tweak this for higher security at the cost of inconvenience.
 - `advertise=True` will send an info-level message via django.contrib.messages with a link to the main django-multifactor page that allows them to add factors for future use. This is useful to increase optional uptake when introducing multifactor to an organisation.


 You can also wrap entire branches of your URLs using [`django-decorator-include`](https://pypi.org/project/django-decorator-include/):

    from decorator_include import decorator_include
    from multifactor.decorators import multifactor_protected

    urlpatterns = [
        path('admin/multifactor/', include('multifactor.urls')),
        path('admin/', decorator_include(multifactor_protected(factors=1), admin.site.urls)),
        ...
    ]


## TODO

 - Allow custom handlers for simple OTP sending.
 - Allow settings to limit what can be added.
 - Allow `multifactor_protected` to require more than one secondary factor.