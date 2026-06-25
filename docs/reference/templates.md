# Templates reference

Every template the package ships, in the order you'll typically want to
override them. Source: `multifactor/templates/multifactor/`.

Override by placing a file with the same path in your project's template
search path (see [Branding](../guides/branding.md) for details).

## High-value overrides

| Template | Renders | Useful context |
| --- | --- | --- |
| `multifactor/brand.html` | Empty placeholder slotted above the `<h1>` on every page. Override to inject your logo and a one-liner. | All standard context (request, user, messages). |
| `multifactor/email.html` | HTML body of the fallback email when `HTML_EMAIL=True`. | `user`, `message` (plain-text body containing the OTP). |
| `multifactor/base.html` | Outer layout used by all package pages. Override only if you want the multifactor pages to inherit from your site shell. | Standard. |

## Page templates

These render the user-facing flows. Override any of them to restyle.

| Template | Purpose |
| --- | --- |
| `multifactor/home.html` | The manage-factors landing page (`views.List`). Lists user keys with rename/toggle/delete actions. |
| `multifactor/add.html` | The factor-type picker (`views.Add`). Lists available factors per `MULTIFACTOR["FACTORS"]`. |
| `multifactor/authenticate.html` | The factor-selection page during a challenge (`views.Authenticate`). |
| `multifactor/help.html` | Static help page (`views.Help`). |
| `multifactor/userkey_form.html` | The rename form (`views.Rename`). |
| `multifactor/FIDO2/add.html` | WebAuthn registration UI. **Contains JavaScript** that talks to `multifactor:fido2_register`. Read carefully before overriding. |
| `multifactor/FIDO2/check.html` | WebAuthn challenge UI. **Contains JavaScript** that talks to `multifactor:fido2_authenticate`. |
| `multifactor/TOTP/add.html` | TOTP enrolment — renders the QR code and the verify input. |
| `multifactor/TOTP/check.html` | TOTP challenge — single 6-digit input. |
| `multifactor/fallback/auth.html` | Fallback OTP entry form. Shows "we sent your code via …" line. |
| `multifactor/fallback/email.html` | HTML email body (same as `multifactor/email.html`; alias). |

## Override worked example

```text
my_project/
└── templates/
    └── multifactor/
        ├── brand.html              # logo + tagline
        ├── email.html              # HTML email branding
        └── home.html               # custom manage page
```

```python
# settings.py
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        # ...
    }
]
```

The order matters: with `DIRS` containing `BASE_DIR / "templates"`, your
overrides win over the package's templates.

## See also

- [Branding](../guides/branding.md) — narrative guide.
- [URLs reference](urls.md) — which view renders which template.
