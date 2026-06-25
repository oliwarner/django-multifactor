# multifactor.urls

The package's `urls.py` (source: `multifactor/urls.py`) registers
`app_name="multifactor"`, so all reverse lookups take the form
`multifactor:<name>`.

## Routes

| Name | URL pattern | View |
| --- | --- | --- |
| `multifactor:home` | `""` (`/`) | `views.List` — list current user's factors. |
| `multifactor:action` | `<str:action>:<slug:ident>/` | `views.List` — perform an action (toggle / delete) on a single factor. |
| `multifactor:help` | `help/` | `views.Help` — static help page. |
| `multifactor:authenticate` | `authenticate/` | `views.Authenticate` — factor-selection page during a challenge. |
| `multifactor:add` | `add/` | `views.Add` — factor-type picker for enrolment. |
| `multifactor:rename` | `rename/<int:pk>/` | `views.Rename` — rename a `UserKey`. |
| `multifactor:fido2_start` | `fido2/new/` | Static template `multifactor/FIDO2/add.html` (hosts the WebAuthn JS). |
| `multifactor:fido2_auth` | `fido2/auth/` | Static template `multifactor/FIDO2/check.html` (hosts the WebAuthn JS). |
| `multifactor:fido2_register` | `fido2/register/` | `factors.fido2.Register` — XHR endpoint for begin/complete. |
| `multifactor:fido2_authenticate` | `fido2/authenticate/` | `factors.fido2.Authenticate` — XHR endpoint for begin/complete. |
| `multifactor:totp_start` | `totp/new/` | `factors.totp.Create` — generate secret + QR + verify enrolment. |
| `multifactor:totp_auth` | `totp/auth/` | `factors.totp.Auth` — verify a TOTP code during challenge. |
| `multifactor:fallback_auth` | `fallback/auth/` | `factors.fallback.Auth` — generate + verify a fallback OTP. |

## Common reverse calls

```python
from django.urls import reverse

reverse("multifactor:home")  # /admin/multifactor/
reverse("multifactor:authenticate")  # /admin/multifactor/authenticate/
reverse("multifactor:add")  # /admin/multifactor/add/
reverse("multifactor:fido2_authenticate")  # /admin/multifactor/fido2/authenticate/
```

The `multifactor:action` route is special — it accepts a `:`-separated tuple
in a single URL component (e.g. `delete:42/`). The actions accepted are
`"toggle"`, `"delete"`, and `"disable_fallback"`. See `views.List` for the
exact dispatch.

## Where to mount

There is no convention enforced by the package. Common placements:

- `path("admin/multifactor/", include("multifactor.urls"))` — under your
  admin, behind staff auth.
- `path("account/security/", include("multifactor.urls"))` — under the user
  account area.

Pick what suits your URL hierarchy. The `app_name` ensures named-URL lookups
keep working regardless.

## See also

- [Architecture](../concepts/architecture.md) — which view talks to which other piece.
- [Branding](../guides/branding.md) — overriding the templates these views render.
