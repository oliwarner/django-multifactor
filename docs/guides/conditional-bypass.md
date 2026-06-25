# Conditional bypass

There are legitimate reasons to skip MFA for specific requests — admin
impersonation, automated end-to-end tests, internal network requests.
`django-multifactor` exposes this via the `BYPASS` setting. **Every bypass is
a hole; use sparingly.**

## How it works

```python
MULTIFACTOR = {
    "BYPASS": "myapp.auth.my_bypass_check",
}
```

`BYPASS` is a dotted path to a single function taking the current `HttpRequest`
and returning truthy/falsy. It is consulted by `common.is_bypassed(request)`,
which is called from both the decorator and the mixins. When it returns truthy,
the MFA gate is silently skipped — the request proceeds as if no MFA was
required.

The function runs **on every request** to every MFA-protected view. Keep it
cheap.

## Recipe — bypass while impersonating

Sites using [django-loginas](https://github.com/skorokithakis/django-loginas)
typically want admins to be able to impersonate ordinary users without
juggling their MFA factors:

```python
# myapp/auth.py
from loginas.utils import is_impersonated_session


def bypass_when_impersonating(request):
    return is_impersonated_session(request)
```

```python
MULTIFACTOR = {
    "BYPASS": "myapp.auth.bypass_when_impersonating",
}
```

## Recipe — bypass during local development

```python
def bypass_when_debug(request):
    from django.conf import settings

    return settings.DEBUG
```

```{caution}
This is convenient but dangerous — a single misconfigured production server
with `DEBUG=True` will silently disable MFA. Prefer the explicit
environment-variable check below for anything that can reach prod.
```

## Recipe — bypass for tests only

```python
import os


def bypass_in_tests(request):
    return os.environ.get("DJANGO_MULTIFACTOR_DISABLE") == "1"
```

Then in your CI: `DJANGO_MULTIFACTOR_DISABLE=1 pytest`. Production never sets
the env var, so it stays on.

## Recipe — bypass for internal network

```python
import ipaddress

INTERNAL = [ipaddress.ip_network("10.0.0.0/8"), ipaddress.ip_network("192.168.0.0/16")]


def bypass_internal(request):
    try:
        addr = ipaddress.ip_address(request.META.get("REMOTE_ADDR", ""))
    except ValueError:
        return False
    return any(addr in net for net in INTERNAL)
```

```{warning}
`REMOTE_ADDR` may be your reverse proxy unless you've configured
`SECURE_PROXY_SSL_HEADER` correctly. Validate the chain end-to-end before
trusting it for security decisions.
```

## What bypass does **not** do

- It does **not** create an MFA session entry. Users bypassed via `BYPASS`
  have `active_factors == []`. A view that inspects `active_factors` directly
  will still see "not authenticated".
- It does **not** prevent the user from voluntarily registering or
  authenticating factors. They can still use `/admin/multifactor/` normally.
- It does **not** persist. Each request re-runs the bypass function.

## Stacking bypasses

`BYPASS` accepts only a **single** dotted path. To combine multiple checks,
write a wrapper:

```python
def composite_bypass(request):
    from .auth import (
        bypass_when_impersonating,
        bypass_internal,
    )

    return bypass_when_impersonating(request) or bypass_internal(request)
```

## Auditing bypasses

Every bypass is an MFA hole. At a minimum:

- Log when bypass fires, with `user.pk`, `request.path`, and the reason.
- Add an alert when bypass fires more than expected (e.g. impersonation on
  a non-admin user).
- Make sure your security team knows the bypass conditions exist.

```python
import logging

log = logging.getLogger("multifactor.bypass")


def bypass_when_impersonating(request):
    from loginas.utils import is_impersonated_session

    if is_impersonated_session(request):
        log.info(
            "MFA bypassed via impersonation; user=%s path=%s",
            request.user.pk,
            request.path,
        )
        return True
    return False
```

## See also

- [Threat model](../security/threat-model.md) — what bypass means for your
  guarantees.
- [`is_bypassed` reference](../reference/common.md).
