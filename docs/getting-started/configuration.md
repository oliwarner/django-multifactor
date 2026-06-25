# Configuration

`django-multifactor` is configured via a single dict, `settings.MULTIFACTOR`.
Every key is optional and falls back to a default defined in
`multifactor/app_settings.py`. This page covers the **commonly-tuned** settings
in context; for a complete table of every key, see the
[settings reference](../reference/settings.md).

## Anatomy of MULTIFACTOR

```python
# settings.py
from django.utils.translation import gettext_lazy as _

MULTIFACTOR = {
    # ---- WebAuthn / FIDO2 ----
    "FIDO_SERVER_ID": "example.com",
    "FIDO_SERVER_NAME": "My Django App",
    "FIDO_SERVER_ICON": None,
    # ---- TOTP authenticator apps ----
    "TOKEN_ISSUER_NAME": "My Django App",
    # ---- Available factor types ----
    "FACTORS": ["FIDO2", "TOTP"],
    # ---- Fallback OTP transports ----
    "FALLBACKS": {
        "email": (lambda user: user.email, "multifactor.factors.fallback.send_email"),
    },
    "HTML_EMAIL": True,
    # ---- Session re-checking ----
    "RECHECK": True,
    "RECHECK_MIN": 60 * 60 * 3,  # 3 hours
    "RECHECK_MAX": 60 * 60 * 6,  # 6 hours
    # ---- Post-login behaviour ----
    "LOGIN_CALLBACK": False,
    "SHOW_LOGIN_MESSAGE": True,
    "LOGIN_MESSAGE": _(
        'You are now multifactor-authenticated. <a href="{}">Multifactor settings</a>.'
    ),
    # ---- Conditional bypass ----
    "BYPASS": None,
}
```

## FIDO2 settings

| Key | Default | Purpose |
| --- | --- | --- |
| `FIDO_SERVER_ID` | `"example.com"` | **The WebAuthn RP ID — the domain in the user's address bar.** Must be exact. `sub.example.com` is acceptable when users hit a subdomain. Read [FIDO2 troubleshooting](../debugging/fido2-troubleshooting.md) if registration fails. |
| `FIDO_SERVER_NAME` | `"Django App"` | Human-readable name shown by browsers in the WebAuthn prompt. |
| `FIDO_SERVER_ICON` | `None` | Optional URL to an icon shown alongside the name on some platforms. |

## TOTP settings

| Key | Default | Purpose |
| --- | --- | --- |
| `TOKEN_ISSUER_NAME` | `"Django App"` | The label that appears next to the account name inside the user's authenticator app. Make this recognisable — users will see it every time they log in. |

## Restricting available factors

The `FACTORS` list controls which factors users can choose when adding a new
one. Removing a factor here does **not** disable previously-registered keys of
that type — those keep working until you delete them through the admin.

```python
MULTIFACTOR = {
    # FIDO2-only — useful for staff-only sites where you can mandate hardware keys.
    "FACTORS": ["FIDO2"],
}
```

## RECHECK — automatic re-prompts

After a successful MFA challenge the session records a random expiry between
`RECHECK_MIN` and `RECHECK_MAX` seconds. When the user next hits a protected
view past that timestamp they are challenged again.

- Set `RECHECK = False` to never re-prompt. (Not recommended for production.)
- Lower the window (e.g. 15–30 minutes) for high-security applications.
- See [recheck tuning](../security/recheck-tuning.md) for guidance.

The random jitter prevents synchronised re-prompts hitting your auth path at
the top of each hour.

## SHOW_LOGIN_MESSAGE / LOGIN_MESSAGE

After a successful MFA challenge the user sees a one-line `messages.info`
banner pointing at the manage-factors page. You can:

- Suppress it entirely: `"SHOW_LOGIN_MESSAGE": False`.
- Customise the wording: provide a `gettext_lazy` translatable string that
  contains `{}` — a single placeholder for the manage-factors URL.

## LOGIN_CALLBACK

By default, after MFA completes the user is redirected to the URL they were
heading to (`session["multifactor-next"]`), or `settings.LOGIN_URL` if no
target was set. If you need a custom post-authentication redirect (e.g. to a
2FA-only landing page), supply a dotted import path:

```python
MULTIFACTOR = {
    "LOGIN_CALLBACK": "myapp.auth.after_mfa",
}
```

The callable is invoked as `callback(request, username=...)` and must return
an `HttpResponse`.

## BYPASS — conditional skip

```python
def bypass_when_impersonating(request):
    from loginas.utils import is_impersonated_session

    return is_impersonated_session(request)


MULTIFACTOR = {
    "BYPASS": "myapp.auth.bypass_when_impersonating",
}
```

`BYPASS` is a dotted path to a function accepting a request. When it returns
truthy, MFA is silently skipped for that request. Use sparingly — every bypass
is a hole. See [conditional bypass](../guides/conditional-bypass.md).

## FALLBACKS — out-of-band one-time passwords

```python
MULTIFACTOR = {
    "FALLBACKS": {
        "email": (lambda user: user.email, "multifactor.factors.fallback.send_email"),
        "sms": (lambda user: user.profile.phone, "myapp.mfa.send_sms"),
    },
}
```

Each entry maps a name to a tuple of `(predicate, dotted_callable)`. The
predicate decides whether this transport is usable for a given user; the
callable does the sending. When the user clicks "forgot your device?" the
package fans out the same OTP to **every** transport whose predicate returns
truthy, so a compromised email account doesn't silently bypass MFA. Full walk-
through in the [custom fallback guide](../guides/custom-fallback.md).

## Where next?

- Want the full table with every key and type? [Settings reference](../reference/settings.md).
- Building your first protected view? [First protected view](first-protected-view.md).
