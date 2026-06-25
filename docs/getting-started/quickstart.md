# Quickstart

This guide gets you from a freshly-installed package to a working MFA challenge
in about five minutes. It assumes you have already followed [Installation](installation.md).

## 1. Register a factor against your own account

Visit `/admin/multifactor/` while logged in. Click **Add factor**. You'll be
asked to pick between FIDO2 and TOTP.

- **TOTP** is the easiest to test — install Google Authenticator, Authy, or
  1Password on your phone (or use the desktop equivalents) and scan the QR code.
- **FIDO2** requires HTTPS or `localhost`. On `localhost` your browser will
  accept Touch ID, Windows Hello, or a USB security key as the second factor.

After registering a factor, the **Manage factors** page will list it. You are
now considered multifactor-authenticated for the current session.

## 2. Protect a view

Pick any view that you'd like to require MFA. Wrap it with the
`@multifactor_protected` decorator:

```python
# views.py
from multifactor.decorators import multifactor_protected


@multifactor_protected(factors=1)
def billing(request):
    return render(request, "billing.html")
```

The decorator parameters are:

| Parameter | Default | Effect |
| --- | --- | --- |
| `factors` | `0` | Minimum number of active, currently-authenticated factors required. `0` means "only challenge users that already have a key set up". |
| `user_filter` | `None` | A `User.objects.filter()`-style dict. Users not matching the filter are let through without challenge. Useful for "staff only need MFA". |
| `max_age` | `0` | Seconds since last successful MFA challenge before the user must re-authenticate. `0` means "no time limit (rely on RECHECK)". |
| `advertise` | `False` | When `factors=0` and the user has no factors yet, show a one-time `messages.info()` banner inviting them to add one. |

## 3. Try it out

Open `/billing/` in a second browser, or in an incognito window where you've
logged in but not yet completed MFA. You should be redirected to
`/admin/multifactor/authenticate/`, prompted to enter your TOTP code or tap
your security key, and then bounced back to `/billing/` once verified.

## 4. Protect an entire URL tree

The decorator also works against `include()` via
[`django-decorator-include`](https://pypi.org/project/django-decorator-include/):

```python
from decorator_include import decorator_include
from multifactor.decorators import multifactor_protected

urlpatterns = [
    path("admin/multifactor/", include("multifactor.urls")),
    path(
        "admin/",
        decorator_include(multifactor_protected(factors=1), admin.site.urls),
    ),
    # ...
]
```

This requires MFA on every URL inside Django's admin. Common pattern.

## 5. What if my user loses their phone?

That's what **fallback OTP** is for. By default, `django-multifactor` will
email a one-time code to the user's `user.email` address when they click
"forgot your device?" on the challenge screen. You can disable that, change
the recipient, add SMS, or replace the whole transport — see the
[custom fallback guide](../guides/custom-fallback.md).

## Where next?

- Want users to add factors **voluntarily** before you require them? Set
  `factors=0, advertise=True` on your most-visited authenticated view and the
  package will gently nag them.
- Want different rules for staff vs members? See
  [Protecting views](../guides/protecting-views.md#dynamic-factor-requirements).
- Going to production? Read [Security best practices](../security/best-practices.md)
  next.
