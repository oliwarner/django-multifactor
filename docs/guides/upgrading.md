# Upgrading

`django-multifactor` follows [SemVer](https://semver.org/) loosely — patch
releases are safe, minor releases may add new settings and bump Python/Django
floors, and major releases may include schema changes. Always read the
release notes on the GitHub releases page before upgrading production.

## General upgrade procedure

1. **Read the release notes.** Linked from
   <https://github.com/oliwarner/django-multifactor/releases>.
2. **Bump the version** in `pyproject.toml` / `requirements.txt`.
3. `pip install -U django-multifactor` (or `poetry update django-multifactor`).
4. `python manage.py migrate multifactor`.
5. `python manage.py collectstatic` if JavaScript files have changed.
6. Run your test suite.
7. Restart your application servers.

## Specific upgrade notes

### Security update — TOTP window, attempt limiting, fallback route

This release hardens one-time-code authentication. It changes behaviour, so
read it before upgrading.

| Change | Before | Now |
| --- | --- | --- |
| TOTP window | hard-coded `60` steps (±30 min, 121 valid codes) | `MULTIFACTOR["TOTP_WINDOW"]`, default **`1`** (±30 s, 3 codes) |
| Replay of a used TOTP code | accepted within the window | rejected (`last_step` stored on the key) |
| Failed TOTP / fallback attempts | unlimited | `MAX_ATTEMPTS` (default **5**) per `ATTEMPT_PERIOD` (default **300 s**), then logout and lockout |
| Fallback route with `FALLBACKS = {}` | still mounted and accepting OTPs | returns **404** |
| Fallback OTP | variable-length, `random` | 8 digits, `secrets` |

What you need to do:

1. **Check your cache.** Attempt limiting needs a cache shared between
   workers. With `DummyCache` it silently does nothing (run
   `manage.py check` for `multifactor.W001`). Set `MAX_ATTEMPTS: 0` only if
   you rate-limit elsewhere.
2. **Expect more TOTP rejections from users with drifting clocks.** Fix the
   clocks first. If you have to, set `TOTP_WINDOW` to `3`. To restore the old
   behaviour exactly (not recommended) set it to `60`.
3. **If you subclassed `totp.Auth` or `Create`**, note that `WINDOW` is gone from
   `multifactor.factors.totp`; read `mf_settings["TOTP_WINDOW"]` instead.
4. **If you disabled fallback with `FALLBACKS = {}`**, links to
   `multifactor:fallback_auth` will now 404. This is intended.
5. Existing TOTP keys need no migration; `last_step` is added on first use.

### 0.6 — U2F removal

U2F (the predecessor to FIDO2/WebAuthn) was removed entirely in 0.6. If you
have users still on U2F:

- Pin to `django-multifactor<0.6` until you can migrate.
- U2F keys typically work as FIDO2 keys without re-registration **only if**
  the browser maps them through the U2F-FIDO2 backwards-compatibility shim.
  Test against your specific key brand before upgrading.
- Worst case: ask affected users to re-enrol with their U2F key as a FIDO2
  credential.

### 0.8 → 0.9 — Python and Django floors

`django-multifactor 0.9` drops support for:

- Python < 3.10
- Django < 5.2

If you are on older versions, pin to `django-multifactor==0.8.4`. Plan a
combined Django + Python + multifactor upgrade rather than chasing the
floors one-by-one.

### Settings deprecations

There are no setting deprecations at the time of writing. The `MULTIFACTOR`
dict has been backwards-compatible across recent minor versions; missing
keys fall back to the defaults in `app_settings.py`.

## What you should re-test on every upgrade

Even patch releases — a five-minute smoke is cheap insurance:

- [ ] Add a new FIDO2 key (uses freshly-shipped JS).
- [ ] Add a new TOTP key (uses pyotp + QR rendering).
- [ ] Authenticate with each existing factor type.
- [ ] Trigger the fallback OTP and confirm at least one transport works.
- [ ] Hit a `factors=2` view if you have one — confirms factor counting.
- [ ] Force a recheck (set `RECHECK_MIN=10` in dev) and confirm re-prompt.

## See also

- [Release process](../contributing/release-process.md) — how versions get cut.
- The full settings reference: [Settings](../reference/settings.md).
