# multifactor.models

```python
from multifactor.models import UserKey, DisabledFallback, KeyTypes, DOMAIN_KEYS
```

Two models, one `TextChoices`. Source: `multifactor/models.py`.

## KeyTypes

```python
class KeyTypes(models.TextChoices):
    FIDO2 = "FIDO2", _("FIDO2 Security Device")
    TOTP = "TOTP", _("TOTP Authenticator")
```

`DOMAIN_KEYS = KeyTypes.FIDO2` — used internally to flag key types that are
scoped to a single domain. Currently only FIDO2 qualifies.

## UserKey

One row per registered factor (FIDO2 or TOTP). Fallback OTP does not create
rows.

| Field | Type | Notes |
| --- | --- | --- |
| `user` | `ForeignKey(AUTH_USER_MODEL, CASCADE, related_name="multifactor_keys")` | Deletes when the user is deleted. |
| `name` | `CharField(max_length=30, null=True, blank=True)` | User-chosen nickname (e.g. "Work YubiKey"). Optional. |
| `properties` | `JSONField(null=True)` | Key-type-specific blob. See below. |
| `key_type` | `CharField(max_length=25, choices=KeyTypes.choices)` | `"FIDO2"` or `"TOTP"`. |
| `enabled` | `BooleanField(default=True)` | Toggle without deleting. Admin sets this for emergency disable. |
| `added_on` | `DateTimeField(auto_now_add=True)` | Immutable. |
| `expires` | `DateTimeField(null=True, blank=True)` | Reserved for future use. Currently not enforced by the package. |
| `last_used` | `DateTimeField(null=True, blank=True)` | Updated by `common.write_session()` on every successful verification. |

### `properties` schema by key type

| `key_type` | `properties` contents |
| --- | --- |
| `FIDO2` | `{"device": <websafe-base64 AttestedCredentialData>, "type": "public-key", "domain": "<RP ID at registration>"}` |
| `TOTP` | `{"secret_key": "<base32 secret>"}` |

### Methods / properties

- `__str__()` — e.g. `'FIDO2 Security Device, aka "Work YubiKey" for alice'`.
- `display_name()` — name + type, or just type.
- `device` — for FIDO2, returns `properties["type"]` (e.g. `"public-key"`).
  Empty string for other key types.
- `auth_url` — the named URL pattern used to verify this key type. Built via
  `common.method_url(key_type)`.

## DisabledFallback

One row per (user, fallback transport name) opted-out pair.

| Field | Type | Notes |
| --- | --- | --- |
| `user` | `ForeignKey(AUTH_USER_MODEL, CASCADE, related_name="+")` | No reverse accessor. |
| `fallback` | `CharField(max_length=50)` | The key from `MULTIFACTOR["FALLBACKS"]`, e.g. `"sms"`. |

There is no admin UI for these by default; create them programmatically
when the user opts out:

```python
DisabledFallback.objects.get_or_create(user=request.user, fallback="sms")
```

## Migrations

```text
multifactor/migrations/
├── 0001_initial.py
├── 0002_auto_20190823_2128.py
├── 0003_userkey_name.py
└── 0004_alter_userkey_key_type.py
```

If you encrypt `UserKey.properties` (recommended for highly-regulated
environments), you will need a data migration that round-trips every row.
Plan for downtime — the table is small but encryption changes the schema.

## See also

- [Concepts: architecture](../concepts/architecture.md) — where these tables fit.
- [Concepts: session model](../concepts/session-model.md) — session state.
