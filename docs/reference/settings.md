# Settings reference

Every key in the `MULTIFACTOR` settings dict, exhaustive. Defaults are pulled
from `multifactor/app_settings.py` — keep this page in sync when adding new
keys.

```python
from django.conf import settings

settings.MULTIFACTOR = {...}
```

If a key is absent from `MULTIFACTOR`, the default below is used. There is no
need to set keys you're not changing.

## Full table

| Key | Type | Default | Purpose |
| --- | --- | --- | --- |
| `LOGIN_MESSAGE` | `str \| lazy` | `"You are now multifactor-authenticated. <a href=\"{}\">Multifactor settings</a>."` | Flash message shown after a successful MFA challenge. Must contain a single `{}` placeholder for the manage-factors URL. |
| `SHOW_LOGIN_MESSAGE` | `bool` | `True` | Whether to show `LOGIN_MESSAGE` at all. |
| `LOGIN_CALLBACK` | `str \| False` | `False` | Dotted import path of a callable `(request, *, username)` that returns an `HttpResponse`. Used to override the post-auth redirect. `False` means "redirect to `settings.LOGIN_URL`". |
| `RECHECK` | `bool` | `True` | Enable periodic re-challenge. When `False`, a verified factor stays verified for the lifetime of the session. |
| `RECHECK_MIN` | `int` (seconds) | `10800` (3 hours) | Earliest possible recheck after verification. |
| `RECHECK_MAX` | `int` (seconds) | `21600` (6 hours) | Latest possible recheck after verification. The actual value per factor is uniformly random in `[MIN, MAX]`. |
| `FIDO_SERVER_ID` | `str` | `"example.com"` | WebAuthn Relying Party ID. **Must** match the user's address-bar domain. See [FIDO2 guide](../guides/fido2.md). |
| `FIDO_SERVER_NAME` | `str` | `"Django App"` | Human-readable RP name shown in the browser's WebAuthn prompt. |
| `FIDO_SERVER_ICON` | `str \| None` | `None` | Optional URL to an icon shown alongside the RP name on some platforms. |
| `TOKEN_ISSUER_NAME` | `str` | `"Django App"` | Label that appears next to the account name inside authenticator apps. |
| `FACTORS` | `list[str]` | `["FIDO2", "TOTP"]` | Factor types offered on the **Add factor** page. Removing a value here does not disable existing keys of that type. |
| `FALLBACKS` | `dict[str, tuple[callable, str]]` | `{"email": (lambda u: u.email, "multifactor.factors.fallback.send_email")}` | Out-of-band OTP transports. Keys are short names, values are `(predicate, dotted_path_to_sender)`. Set to `{}` to disable fallback. |
| `HTML_EMAIL` | `bool` | `True` | Send a multipart text+HTML email when the email fallback transport is used. Set to `False` for text-only. |
| `TOTP_WINDOW` | `int` (steps) | `1` | How many 30-second TOTP steps either side of "now" are accepted. `1` accepts 3 codes (±30 s) and is the RFC 6238 recommendation. The pre-security-release behaviour was a hard-coded `60` (121 codes, ±30 minutes). See [TOTP window](#totp-window). |
| `MAX_ATTEMPTS` | `int` | `5` | Failed TOTP / fallback OTP attempts allowed per user within `ATTEMPT_PERIOD` before the user is logged out and locked out of further attempts. `0` disables the limit. Needs a real [cache](#attempt-limiting). |
| `ATTEMPT_PERIOD` | `int` (seconds) | `300` | How long failed attempts are counted for, and therefore how long a lockout lasts. The clock starts at the first failure. |
| `BYPASS` | `str \| None` | `None` | Dotted import path of a callable `(request)` that returns truthy to skip MFA for this request. See [conditional bypass](../guides/conditional-bypass.md). |

## TOTP window

`TOTP_WINDOW` is the number of 30-second steps accepted either side of the
current one.

| `TOTP_WINDOW` | Valid codes at once | Device clock tolerance | Guesses for a 50% chance (1,000,000 codes) |
| --- | --- | --- | --- |
| `1` (default) | 3 | ±30 s | ~231,000 |
| `3` | 7 | ±90 s | ~99,000 |
| `60` (old behaviour) | 121 | ±30 min | ~5,700 |

Keep it at `1` unless you have users with demonstrably drifting clocks, and
fix the clock (NTP on the server, automatic time on the device) before raising
it. Each increase makes guessing proportionally easier. The same value is used
when enrolling a new authenticator.

Each accepted code is also recorded against the key (`properties["last_step"]`)
and cannot be used again, nor can any earlier code.

## Attempt limiting

Failed TOTP and fallback-OTP attempts are counted **per user**, in a single
shared counter, so alternating between the two factors doesn't give extra
guesses. When `MAX_ATTEMPTS` failures happen within `ATTEMPT_PERIOD` seconds
the user is logged out, a `WARNING` is logged to `multifactor.throttle`, and
every further attempt is refused until the period ends, even with a correct
code. A successful verification resets the counter.

- **Needs a cache.** Counters use Django's default cache. `DummyCache` forgets
  everything (a system check, `multifactor.W001`, warns about this) and
  `LocMemCache` is per-process, so with several workers the effective limit is
  multiplied. Use Redis, Memcached or the database cache in production.
- **A cache outage blocks OTP logins.** The counters are read and written on
  every TOTP and fallback attempt. If the cache backend is unreachable (for
  example Redis is down) and raises, those views return a 500 and users can't
  complete a TOTP or fallback challenge until it recovers. This fails closed
  on purpose: swallowing the error would let anyone who can disrupt the cache
  guess codes without limit. FIDO2 does not use the cache and is unaffected.
  Monitor your cache as you would a database, and if you need to keep logins
  working through an outage, set `MAX_ATTEMPTS` to `0` and rate-limit at the
  edge instead.
- **Per user, not per IP.** Someone who knows a user's password can therefore
  lock that user out of MFA for `ATTEMPT_PERIOD`. This is the usual trade-off;
  the alternative is unlimited guessing. Add per-IP limiting at your proxy or
  with `django-ratelimit` as well.
- **Not a replacement** for a rate limit in front of your application. See
  [best practices](../security/best-practices.md#4-rate-limit-the-mfa-endpoints).

## Common patterns

### Tight production defaults

```python
MULTIFACTOR = {
    "FIDO_SERVER_ID": "app.example.com",
    "FIDO_SERVER_NAME": "Acme",
    "TOKEN_ISSUER_NAME": "Acme",
    "FACTORS": ["FIDO2", "TOTP"],
    "RECHECK": True,
    "RECHECK_MIN": 60 * 60,  # 1 hour
    "RECHECK_MAX": 60 * 60 * 2,  # 2 hours
    "HTML_EMAIL": True,
}
```

### Permissive dev defaults (e.g. testsite)

```python
MULTIFACTOR = {
    "FIDO_SERVER_ID": os.environ.get("DOMAIN", "localhost"),
    "FALLBACKS": {
        "debug-console": (
            lambda u: u,
            "multifactor.factors.fallback.debug_print_console",
        ),
        "email": (lambda u: u.email, "multifactor.factors.fallback.send_email"),
    },
}
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
```

### High-security tight loop

```python
MULTIFACTOR = {
    "FIDO_SERVER_ID": "vault.example.com",
    "FIDO_SERVER_NAME": "Vault",
    "FACTORS": ["FIDO2"],  # no TOTP — hardware keys only
    "FALLBACKS": {},  # no escape hatch
    "RECHECK": True,
    "RECHECK_MIN": 15 * 60,  # 15 minutes
    "RECHECK_MAX": 30 * 60,  # 30 minutes
}
```

## See also

- [Architecture](../concepts/architecture.md) — where these settings are read.
- [Security best practices](../security/best-practices.md) — choosing values
  for your threat model.
