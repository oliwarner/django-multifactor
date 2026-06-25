# Running the bundled testsite

The repository ships a minimal Django site at `testsite/` that's
preconfigured for local development of `django-multifactor` itself. It's the
fastest way to exercise the package end-to-end without setting up a project
of your own.

## What's in the testsite

```text
testsite/
├── manage.py
└── testsite/
    ├── __init__.py
    ├── settings.py
    ├── urls.py
    └── disable_csrf.py
```

Highlights of `settings.py`:

- SQLite database at `testsite/db.sqlite3`.
- `DEBUG = True`, `ALLOWED_HOSTS = ["*"]`.
- `FIDO_SERVER_ID` read from the `DOMAIN` environment variable, defaulting
  to `localhost`.
- Email goes to the console backend (`debug_print_console` also registered
  as a fallback).
- `DisableCSRFMiddleware` strips CSRF protection — convenient for testing,
  **never copy this to a real site**.

## Running it

```bash
cd /path/to/django-multifactor
pip install -e .                 # install the package in editable mode
pip install django-extensions django-debug-toolbar django-decorator-include

# from the repo root:
PYTHONPATH=. DJANGO_SETTINGS_MODULE=testsite.testsite.settings python testsite/manage.py migrate
PYTHONPATH=. DJANGO_SETTINGS_MODULE=testsite.testsite.settings python testsite/manage.py createsuperuser
PYTHONPATH=. DJANGO_SETTINGS_MODULE=testsite.testsite.settings python testsite/manage.py runserver
```

Or, using the same env that the tox/test matrix uses:

```bash
tox -e py313-django52
```

…which exercises the test suite. For interactive use, the explicit
`runserver` invocation is friendlier.

## Browsing

- `http://localhost:8000/admin/` — Django admin (log in with your superuser).
- `http://localhost:8000/admin/multifactor/` — manage factors.

Register a TOTP factor first — it works without any extra setup. For
FIDO2 on `localhost`, modern browsers will offer Touch ID / Windows Hello.
For testing a USB key against a real domain, see the
[FIDO2 troubleshooting](fido2-troubleshooting.md) section on Cloudflare
Tunnel / ngrok.

## Testing fallback OTPs

The testsite registers two fallback transports:

```python
MULTIFACTOR = {
    "FALLBACKS": {
        "debug-console": (
            lambda u: u,
            "multifactor.factors.fallback.debug_print_console",
        ),
        "email": (lambda u: u.email, "multifactor.factors.fallback.send_email"),
    },
}
```

When you trigger fallback, the OTP is printed to the `runserver` console
**and** sent to the console email backend (also shows up in the same
console). Read it from there and type it into the form.

## Testing custom transports

To exercise a custom transport while developing, edit `testsite/testsite/settings.py`
directly and add your transport to `MULTIFACTOR["FALLBACKS"]`:

```python
MULTIFACTOR["FALLBACKS"]["mine"] = (lambda u: True, "myapp.send_mine")
```

You'll need `myapp` on `PYTHONPATH`. The simplest is to drop a tiny module
next to `testsite/testsite/`:

```python
# testsite/testsite/myapp.py
def send_mine(user, message):
    print("MINE:", user, message)
    return "mine"
```

Then reference it as `"testsite.testsite.myapp.send_mine"`.

## Resetting the database

```bash
rm testsite/db.sqlite3
PYTHONPATH=. DJANGO_SETTINGS_MODULE=testsite.testsite.settings python testsite/manage.py migrate
PYTHONPATH=. DJANGO_SETTINGS_MODULE=testsite.testsite.settings python testsite/manage.py createsuperuser
```

A fresh start is often the fastest path when sessions are stuck.

## Caveats

- **`DisableCSRFMiddleware` is in MIDDLEWARE.** Don't copy this site's
  settings into a real project. It exists so we can POST without CSRF
  tokens during automated testing.
- **`SECRET_KEY` is hardcoded** in `settings.py`. Fine for testing,
  catastrophic for production.
- **`ALLOWED_HOSTS = ["*"]`** lets the dev server respond to any Host
  header. Convenient with Cloudflare Tunnel; never appropriate for prod.

## See also

- [Development setup](../contributing/development-setup.md) — for working
  on the package itself.
- [Running tests](../contributing/running-tests.md).
