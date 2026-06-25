# Branding

`django-multifactor` ships its own templates so that you can drop it in and
get a usable flow with zero front-end work. The styling is deliberately
generic. Users coming from your branded login page might think they've left
your site — this page explains how to fix that without forking the templates.

## Override points

Django's template loader searches your project's template directories first,
then app templates in `INSTALLED_APPS` order. To override any template, create
a file at the same logical path in your own project's templates:

```text
my_project/
└── templates/
    └── multifactor/
        ├── brand.html              <-- the most common override
        ├── email.html              <-- email fallback HTML
        ├── base.html               <-- full layout (rarely needed)
        ├── home.html
        ├── authenticate.html
        ├── FIDO2/
        │   └── add.html
        └── TOTP/
            └── add.html
```

Make sure your `TEMPLATES["DIRS"]` includes `templates/`, **or** your app
appears in `INSTALLED_APPS` **above** `multifactor`.

## The lightweight override: brand.html

`multifactor/brand.html` is an intentionally empty placeholder that ships in
the package. It is rendered immediately above the `<h1>` title on every
factor page. Override it to slot in your logo and a one-liner:

```html
{# my_project/templates/multifactor/brand.html #}
<a href="/">
  <img src="{% static 'logo.svg' %}" alt="Acme" style="height: 48px;">
</a>
<p style="margin-top: .5rem; color: #555;">
  Two-factor authentication for your Acme account.
</p>
```

Tiny override, big perceived-trust win.

## The fallback email template

When the fallback OTP is sent via email and `MULTIFACTOR["HTML_EMAIL"]` is
left at its default `True`, the package also sends an HTML alternative
rendered from `multifactor/email.html`. The template is given two context
variables:

- `user` — the recipient `User` instance.
- `message` — the plain-text body (includes the OTP).

A minimal branded version:

```html
{# my_project/templates/multifactor/email.html #}
<!DOCTYPE html>
<html><body style="font-family: sans-serif;">
  <img src="https://acme.example.com/static/logo.png" alt="Acme">
  <h1>Your one-time code</h1>
  <p>Hi {{ user.get_full_name|default:user.username }},</p>
  <pre style="font-size: 1.5em;">{{ message }}</pre>
  <p style="color: #666;">
    If you didn't try to sign in, please change your password and contact
    <a href="mailto:security@acme.example.com">security@acme.example.com</a>.
  </p>
</body></html>
```

To send plain-text only, set `MULTIFACTOR["HTML_EMAIL"] = False`.

## Full template override

For deeper customisation, copy the relevant template out of
`multifactor/templates/multifactor/` into your project and edit it. The
package's templates use simple semantic markup — they should drop into
Bootstrap, Tailwind or your in-house design system with cosmetic CSS only.

Files that are reasonable to override:

- `home.html` — the manage-factors landing page.
- `authenticate.html` — the factor-selection page during a challenge.
- `add.html` — the add-factor picker.
- `userkey_form.html` — the rename-factor form.
- `FIDO2/add.html`, `FIDO2/check.html` — the WebAuthn JS lives here. **Read
  the originals carefully before overriding** — broken JS = broken auth.
- `TOTP/add.html`, `TOTP/check.html` — TOTP setup and challenge.
- `fallback/auth.html` — the fallback OTP entry form.

## Replacing the whole layout (`base.html`)

If your site uses a single global base template (Bootstrap shell, brand
header/footer), you can replace the package's `base.html` to inherit your
site's chrome:

```html
{# my_project/templates/multifactor/base.html #}
{% extends "my_project/base.html" %}

{% block title %}Authentication — Acme{% endblock %}

{% block content %}
  {% block multifactor %}{% endblock %}
{% endblock %}
```

You may need to look at the package's `base.html` to see the exact blocks
exposed by the inner templates.

## Where next?

- [Internationalisation](i18n.md) — translate user-facing strings.
- [Admin integration](admin-integration.md) — surface factors in the Django
  admin.
