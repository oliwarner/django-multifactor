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
| `BYPASS` | `str \| None` | `None` | Dotted import path of a callable `(request)` that returns truthy to skip MFA for this request. See [conditional bypass](../guides/conditional-bypass.md). |

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
