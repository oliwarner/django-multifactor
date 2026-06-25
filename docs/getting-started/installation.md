# Installation

This page walks through installing `django-multifactor` into an existing Django
project. It assumes you already have a working Django site with users that can
log in.

## Requirements

- **Python 3.10+** (3.10, 3.11, 3.12, 3.13, 3.14, 3.15)
- **Django 5.2, 6.0 or 6.1**
- A session backend (the default database backend is fine)
- `django.contrib.messages` installed and wired up
- HTTPS in production — FIDO2/WebAuthn refuses to register or authenticate on
  plain HTTP except against `localhost`

If you are still on older Python or Django, pin to `django-multifactor==0.8.4`
which supported Django 2.2 – 5.2 and Python 3.8 – 3.13. New features will not
be backported.

## Install the package

```bash
pip install django-multifactor
```

Or, with Poetry:

```bash
poetry add django-multifactor
```

The wheel ships templates, static files and the compiled `.mo` translation
catalogs — you do not need to run `compilemessages` against this app in your
own project.

## Add to INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "django.contrib.messages",  # required
    "multifactor",
]
```

`django.contrib.messages` is a hard requirement — `django-multifactor` flashes
user-facing warnings (e.g. "this view needs a second factor") through the
messages framework. If you don't render messages in your base template, those
prompts will be silently dropped.

## Minimal configuration

Add a `MULTIFACTOR` dictionary to your settings. The keys below are the absolute
minimum to make FIDO2 and TOTP work; every other setting has a sensible default.
See the [full settings reference](../reference/settings.md) for the rest.

```python
MULTIFACTOR = {
    "FIDO_SERVER_ID": "example.com",  # MUST match the domain users see in the URL bar
    "FIDO_SERVER_NAME": "My Django App",  # Human-readable name shown by browsers
    "TOKEN_ISSUER_NAME": "My Django App",  # Label that appears in authenticator apps
}
```

```{warning}
`FIDO_SERVER_ID` is the WebAuthn **Relying Party ID** (RP ID). It must be the
registrable domain that the user's browser sees — `example.com` or
`auth.example.com`, **not** `https://example.com/` and **not** an IP address.
If this does not match the site users hit, FIDO2 registration will fail with
opaque browser errors. See [FIDO2 troubleshooting](../debugging/fido2-troubleshooting.md).
```

## Mount the URLs

```python
# urls.py
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/multifactor/", include("multifactor.urls")),
    path("admin/", admin.site.urls),
    # ...
]
```

You can mount the URLs anywhere in your tree. Mounting near (or under) your
login URL is conventional. The included `app_name="multifactor"`, so reverse
lookups look like `reverse("multifactor:home")`.

## Apply database migrations

```bash
python manage.py migrate
```

`django-multifactor` ships two tables — `UserKey` (stores a user's registered
factors) and `DisabledFallback` (records when a user opts out of a fallback
transport). They are small.

## Collect static files

The package ships JavaScript needed for the WebAuthn browser dance. If you
serve static files via `collectstatic`:

```bash
python manage.py collectstatic
```

…and restart Django.

## Verify the install

1. Start your dev server: `python manage.py runserver`.
2. Log in as any user.
3. Visit `/admin/multifactor/` (or wherever you mounted the URLs).
4. You should see the **Manage factors** page with an empty list and an
   **Add factor** button.

If you see a 404, your URL include is wrong. If you see a 500, check the
[common issues](../debugging/common-issues.md) page.

## Where next?

- New to MFA in Django? [Quickstart](quickstart.md) — protect one view in five
  minutes.
- Want to understand what's happening under the hood?
  [Architecture](../concepts/architecture.md).
- Ready to ship to production? [Security best practices](../security/best-practices.md).
