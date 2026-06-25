# django-multifactor

**Drop-in multi-factor authentication for Django.** Ships with standalone views,
opinionated defaults, and a very simple integration pathway to retrofit onto
mature sites.

`django-multifactor` is a **second layer of defence**, not a passwordless system.
It sits on top of Django's existing authentication and asks a logged-in user to
prove themselves with a second factor before sensitive views render.

Supported factors:

- **FIDO2 / WebAuthn** — security keys, Windows Hello, Touch ID, Android
  SafetyNet, NFC.
- **TOTP** — any RFC 6238 authenticator app (Google Authenticator, Authy, 1Password,
  Bitwarden, …).
- **Fallback OTP** — pluggable transports (email by default, plus anything you
  bolt on — SMS, push, in-app messaging, carrier pigeon).

```{note}
U2F was removed in version 0.6. If you still depend on U2F, pin to an older
release and plan a migration to FIDO2.
```

## Who this site is for

This documentation is written so that **a junior developer can get a working MFA
flow in their Django project in under an hour**, while still giving **senior
developers** the architectural depth, security model, and tuning knobs they need
to deploy `django-multifactor` to production with confidence.

If you are brand new, start with [Installation](getting-started/installation.md)
and follow the chapters in order. If you have used `django-multifactor` before,
the [Reference](reference/settings.md) and [Debugging](debugging/common-issues.md)
sections are probably what you want.

## How the docs are organised

| Section | Audience | What you'll find |
| --- | --- | --- |
| [Getting started](getting-started/installation.md) | Junior | Install, configure, protect your first view. |
| [Concepts](concepts/architecture.md) | All | How the package is wired together; full request flow diagrams. |
| [Guides](guides/protecting-views.md) | All | Task-oriented recipes — admin integration, custom fallbacks, branding, i18n. |
| [Reference](reference/settings.md) | All | Every setting, decorator, mixin, model field and named URL. |
| [Security](security/threat-model.md) | Senior | Threat model, hardening, fallback risk, recheck tuning. |
| [Debugging](debugging/common-issues.md) | Senior | Troubleshooting recipes, logging configuration, the bundled testsite. |
| [Contributing](contributing/development-setup.md) | Contributors | Local development, the test matrix, translations, releases. |

## A 10-second taste

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "django.contrib.messages",
    "multifactor",
]

MULTIFACTOR = {
    "FIDO_SERVER_ID": "example.com",
    "FIDO_SERVER_NAME": "My Django App",
    "TOKEN_ISSUER_NAME": "My Django App",
}
```

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    path("admin/multifactor/", include("multifactor.urls")),
    # ...
]
```

```python
# views.py
from multifactor.decorators import multifactor_protected


@multifactor_protected(factors=1)
def billing(request): ...
```

That's it — every user with one or more registered second factors will be sent
through MFA challenge before `billing` renders.

## Table of contents

```{toctree}
:caption: Getting started
:maxdepth: 2

getting-started/installation
getting-started/quickstart
getting-started/configuration
getting-started/first-protected-view
```

```{toctree}
:caption: Concepts
:maxdepth: 2

concepts/architecture
concepts/auth-flow
concepts/session-model
concepts/factors-overview
```

```{toctree}
:caption: Guides
:maxdepth: 2

guides/protecting-views
guides/mixins
guides/fido2
guides/totp
guides/custom-fallback
guides/conditional-bypass
guides/branding
guides/admin-integration
guides/i18n
guides/upgrading
```

```{toctree}
:caption: Reference
:maxdepth: 2

reference/settings
reference/decorators
reference/mixins
reference/models
reference/urls
reference/common
reference/templates
```

```{toctree}
:caption: Security
:maxdepth: 2

security/threat-model
security/best-practices
security/fallback-risks
security/recheck-tuning
security/disclosure
```

```{toctree}
:caption: Debugging
:maxdepth: 2

debugging/common-issues
debugging/logging
debugging/fido2-troubleshooting
debugging/totp-troubleshooting
debugging/session-debugging
debugging/testsite
```

```{toctree}
:caption: Contributing
:maxdepth: 2

contributing/development-setup
contributing/running-tests
contributing/coding-standards
contributing/translations
contributing/release-process
```

```{toctree}
:caption: Changelog
:maxdepth: 1

changelog
```
