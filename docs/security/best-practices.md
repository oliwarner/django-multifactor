# Security best practices

A pragmatic, opinionated checklist for production deployments. Items are
ordered roughly by impact-per-effort.

## 1. HTTPS, properly

```python
# settings.py
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 year, only after testing!
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)  # if behind a TLS-terminating proxy
```

FIDO2 requires HTTPS in production. HSTS prevents downgrade attacks against
your session cookies. Test HSTS with `SECURE_HSTS_SECONDS=300` first;
preload is a one-way trip.

## 2. Lock down cookies

```python
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"  # or "Strict" if cross-site posts aren't needed
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
```

Without `SESSION_COOKIE_SECURE`, a single accidental plain-HTTP request can
leak the session cookie. Without `HttpOnly`, an XSS bug exposes it to
attacker JavaScript.

## 3. Get FIDO_SERVER_ID right

The single biggest source of FIDO2 failures. Re-read [FIDO2 guide](../guides/fido2.md).
Once set, **do not change it** without planning to invalidate every
existing FIDO2 key.

## 4. Rate-limit the MFA endpoints

The package does not rate-limit on its own. Without this, an attacker with
a leaked session can brute-force a 6-digit TOTP or the 8-digit fallback OTP.

Two options:

- **Django middleware** —
  [`django-ratelimit`](https://django-ratelimit.readthedocs.io/) or
  [`django-axes`](https://django-axes.readthedocs.io/) or
  [django-smart-ratelimit](https://github.com/YasserShkeir/django-smart-ratelimit) 
- **Edge** — CloudFlare WAF, AWS WAF, fastly, any reverse proxy.

Rate-limit at a minimum:

- `multifactor:totp_auth`
- `multifactor:fido2_authenticate`
- `multifactor:fallback_auth`

Per IP + per user. 5 attempts per 5 minutes per (user, IP) is a reasonable
starting point.

## 5. Tighten RECHECK and max_age

The default `RECHECK_MIN=3h` / `RECHECK_MAX=6h` is a low-friction default
for moderate-risk applications. For higher-risk:

```python
MULTIFACTOR = {
    "RECHECK_MIN": 60 * 60,  # 1 hour
    "RECHECK_MAX": 60 * 60 * 2,  # 2 hours
}
```

…and per-view `max_age` for the most sensitive things:

```python
@multifactor_protected(factors=1, max_age=5 * 60)
def transfer_funds(request): ...
```

See [recheck tuning](recheck-tuning.md) for guidance.

## 6. Audit factor changes

Hook `post_save` and `post_delete` on `UserKey` and ship the events to your
SIEM:

```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from multifactor.models import UserKey


@receiver([post_save, post_delete], sender=UserKey)
def audit(sender, instance, **kwargs):
    import logging

    logging.getLogger("audit.mfa").info(
        "userkey user=%s type=%s enabled=%s action=%s",
        instance.user_id,
        instance.key_type,
        instance.enabled,
        "saved" if kwargs.get("created") is not None else "deleted",
    )
```

Common alerts:

- **New factor registered** — could be legitimate, or account takeover
  planting a backdoor key.
- **Existing factor disabled in admin** — investigate why.
- **All factors deleted for a user** — almost always a recovery, but worth
  a paper trail.

## 7. Limit who can disable factors

The `MultifactorUserAdmin` inline lets admins toggle `enabled` on any user's
key. Restrict the admin permission accordingly — not every staff user should
be able to disable their colleagues' MFA. Use Django permissions, or split
your `is_staff` boundary into multiple roles.

## 8. Verify email before relying on it for fallback

If your `User` model lets users change `email` without confirmation, the
email fallback's trust assumption is broken — an attacker with the password
can swap the email and receive the OTP themselves. Add email verification
in your user-management flow.

## 9. Encourage backup factors

Users should register **at least two** factors of different types — e.g.
two FIDO2 keys, or one FIDO2 plus one TOTP. Single-factor users are one
lost phone away from a support ticket.

Surface this in your UI ("we recommend adding a second key") on the
`multifactor:home` page.

## 10. Watch for unexpected bypasses

If you use `MULTIFACTOR["BYPASS"]`, **log every fire**. See the example in
[conditional bypass](../guides/conditional-bypass.md). A spike in bypasses
is a bug or an attack — either way, you want to know.

## 11. Pin your dependencies

`pyotp` and `fido2` are security libraries. Upgrade promptly when their
maintainers release fixes. Pin to a minor version range so dependabot
notices CVEs and runs your tests automatically.

## See also

- [Threat model](threat-model.md) — what these mitigate.
- [Fallback risks](fallback-risks.md) — the subtle ones.
- [Recheck tuning](recheck-tuning.md) — picking RECHECK values.
