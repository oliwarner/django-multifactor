# Your first protected view

This page walks through a complete, end-to-end example: a fresh Django project
that gates a "billing" view behind MFA. If you've followed
[Installation](installation.md) you already have most of this — what follows is
a copy-pasteable concrete reference.

## Project layout

```text
myproject/
├── manage.py
├── myproject/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── billing/
    ├── __init__.py
    ├── apps.py
    ├── urls.py
    └── views.py
```

## settings.py — the minimum

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "multifactor",
    "billing",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

MULTIFACTOR = {
    "FIDO_SERVER_ID": "localhost",  # change for prod
    "FIDO_SERVER_NAME": "MyProject (dev)",
    "TOKEN_ISSUER_NAME": "MyProject (dev)",
}

LOGIN_URL = "/admin/login/"  # or wherever your login view lives
```

## myproject/urls.py

```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/multifactor/", include("multifactor.urls")),
    path("admin/", admin.site.urls),
    path("billing/", include("billing.urls")),
]
```

## billing/views.py

```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from multifactor.decorators import multifactor_protected


@login_required
@multifactor_protected(factors=1, max_age=15 * 60)
def billing_home(request):
    """Show recent invoices; requires MFA within the last 15 minutes."""
    return render(request, "billing/home.html", {"invoices": []})
```

```{important}
Order matters: `@login_required` must run **before** `@multifactor_protected`
(i.e. it should appear above it in the decorator stack). MFA only makes sense
for authenticated users, and `multifactor_protected` lets unauthenticated
requests fall through to the rest of your auth stack so `@login_required` can
catch them.
```

## billing/urls.py

```python
from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("", views.billing_home, name="home"),
]
```

## Running it

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

1. Log in at `/admin/login/`.
2. Visit `/admin/multifactor/` and register a TOTP token (FIDO2 also works on
   `localhost`).
3. Open `/billing/`. The page should render — your fresh registration counts
   as an active factor for this session.
4. Wait 16 minutes (or set `max_age=10` while testing) and hit `/billing/`
   again. You'll be redirected through the MFA challenge.

## A more realistic decorator — only staff need MFA

```python
@login_required
@multifactor_protected(factors=1, user_filter={"is_staff": True}, max_age=30 * 60)
def billing_home(request): ...
```

This says: "only require MFA for staff users; ordinary members can read
billing without a second factor; once authenticated, the staff session stays
hot for 30 minutes."

## A dynamic factor requirement

```python
def factor_count(request):
    # Two factors required from off-network; zero on-network.
    return 0 if request.META.get("REMOTE_ADDR", "").startswith("10.") else 2


@multifactor_protected(factors=factor_count)
def billing_home(request): ...
```

`factors` may be a callable — useful for risk-based authentication where the
required count depends on the request itself (IP, hour of day, recent failed
logins, etc.).

## Where next?

- All decorator parameters: [Protecting views](../guides/protecting-views.md).
- Same effect using class-based views: [Mixins](../guides/mixins.md).
