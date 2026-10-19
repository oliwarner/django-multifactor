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
| `MAX_ATTEMPTS` | `int` | `5` | Failures (since the user's last success) that, if they all fall within `ATTEMPT_PERIOD`, lock the user out. Applies to TOTP and fallback OTP together. `0` disables attempt logging and lockout. See [attempt limiting](#attempt-limiting). |
| `ATTEMPT_PERIOD` | `int` (seconds) | `300` | The sliding window in which `MAX_ATTEMPTS` failures trigger a lockout. |
| `LOCKOUT_PERIOD` | `int` (seconds) | `1800` | How long a lockout lasts, measured from the user's most recent failure. Keep it **at least as long as `ATTEMPT_PERIOD`**; see [the lockout length caveat](#keep-lockout_period-at-least-attempt_period). |
| `ATTEMPT_RETENTION_DAYS` | `int` (days) | `90` | Age after which `manage.py prune_mfa_attempts` deletes logged attempts. |
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

Every TOTP and fallback-OTP attempt is stored in the database as an
`AuthAttempt` row (`user`, `factor`, `outcome`, `timestamp`). There is no
separate counter: whether a user is locked out is worked out from those rows.

A user is **locked out** when their most recent `MAX_ATTEMPTS` failures since
their last success all fall within `ATTEMPT_PERIOD` seconds of each other (a
sliding window, not one that resets on a timer). The lockout lasts until
`LOCKOUT_PERIOD` seconds after their latest failure. While locked out:

- the user is logged out and a `WARNING` is logged to `multifactor.throttle`;
- every attempt is refused, even with a correct code, and recorded with outcome
  `blocked`. Blocked attempts are **not** counted as failures, so hammering the
  endpoint can't extend a lockout indefinitely.

A successful verification ends the run of failures. TOTP and fallback share the
one log, so alternating between them doesn't give extra guesses.

With the defaults, an attacker gets 5 guesses and is then locked out for 30
minutes, about 240 guesses a day against one account.

### Keep `LOCKOUT_PERIOD` at least `ATTEMPT_PERIOD`

When a lockout ends, the failures that caused it are still in the log. They
only stop counting against the user because the newest `MAX_ATTEMPTS` failures,
which now include an old one, span more than `ATTEMPT_PERIOD`. That holds only
if `LOCKOUT_PERIOD >= ATTEMPT_PERIOD`.

If you set `LOCKOUT_PERIOD` **shorter** than `ATTEMPT_PERIOD` (say a 60 second
lockout with a 300 second window), the old failures are still inside the window
when the lockout ends. A single new failure then makes the latest
`MAX_ATTEMPTS` failures fit in the window again, and the user is locked out
straight away, with no fresh set of attempts. Don't configure it that way unless
you intend a very strict "one strike" policy after a lockout.
The system check `multifactor.W001` (shown by `manage.py check`) warns when
the settings are configured this way.

- **Uses the database, not the cache.** Nothing depends on how your cache is
  configured or whether it is shared between workers. It adds one small write
  per attempt (plus one more when the code is accepted) and a lockout lookup.
  The user's row is locked while an attempt is reserved so parallel requests
  can't all slip past the limit.
- **Admins can see it.** `AuthAttempt` is registered in the Django admin as a
  read-only log, filterable by outcome and factor. To lift a lockout early,
  delete that user's recent `failure` rows there.
- **Prune it.** Run `manage.py prune_mfa_attempts` periodically (cron or a
  scheduler); it removes rows older than `ATTEMPT_RETENTION_DAYS`, or pass
  `--days N`. The log stores usernames and timestamps only, no IP addresses.
- **Per user, not per IP.** Someone who knows a user's password can lock that
  user out of MFA for `LOCKOUT_PERIOD` by failing deliberately. That is the
  trade-off against unlimited guessing; shorten `LOCKOUT_PERIOD` if it worries
  you more than guessing. Add per-IP limiting at your proxy or with
  `django-ratelimit` as well.
- **Not a replacement** for a rate limit in front of your application, and it
  does not cover FIDO2. See
  [best practices](../security/best-practices.md#4-rate-limit-the-mfa-endpoints).
- **Needs a migration** (`python manage.py migrate multifactor`).

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
