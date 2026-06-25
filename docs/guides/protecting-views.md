# Protecting views

The `@multifactor_protected` decorator is how you tell `django-multifactor`
which views need a second factor. It's a regular function decorator and works
on function-based views, `View.as_view()` (via `method_decorator`), and entire
URL trees (via `decorator_include`).

## Signature

```python
from multifactor.decorators import multifactor_protected


@multifactor_protected(
    factors=0,
    user_filter=None,
    max_age=0,
    advertise=False,
)
def my_view(request): ...
```

| Parameter | Default | Effect |
| --- | --- | --- |
| `factors` | `0` | Minimum number of currently-active factors required. May be an `int` or a callable that receives the request and returns an `int`. |
| `user_filter` | `None` | A dict passed to `User.objects.filter(pk=..., **user_filter)`. If the current user does not match, the request is let through with no challenge. |
| `max_age` | `0` | Seconds since the *most recently verified* factor's `verified_at`. `0` means "no max age" (rely on `RECHECK` for invalidation). |
| `advertise` | `False` | When `factors=0` *and* the user has no factors yet, show a one-time `messages.info()` banner inviting them to add one. |

## The most common shapes

### Soft advert — encourage uptake

```python
@multifactor_protected(factors=0, advertise=True)
def home(request): ...
```

Users without factors see one info banner inviting them to add a second
factor. Users *with* factors are silently challenged. New deployments often
start here to bootstrap adoption.

### One factor required — the default for sensitive views

```python
@multifactor_protected(factors=1)
def billing(request): ...
```

Any one active factor counts. The fallback OTP counts. If you need to
*exclude* the fallback, see the snippet in [Session model](../concepts/session-model.md).

### Multiple factors — defence in depth for the very sensitive

```python
@multifactor_protected(factors=2, max_age=5 * 60)
def export_payroll(request): ...
```

User must have authenticated two distinct factors *within the last 5 minutes*.
For ops dashboards or financial exports.

### Staff-only requirement

```python
@multifactor_protected(factors=1, user_filter={"is_staff": True})
def admin_dashboard(request): ...
```

Non-staff are let straight through; staff are challenged. Useful when MFA
adoption is rolling out gradually.

## Dynamic factor requirements

`factors` accepts a callable. The callable receives the `HttpRequest` and
must return an `int`.

```python
def risk_based_factor_count(request):
    # Internal network — no MFA. Off-network — one factor. Suspicious — two.
    ip = request.META.get("REMOTE_ADDR", "")
    if ip.startswith("10."):
        return 0
    if request.session.get("recent_failed_logins", 0) > 3:
        return 2
    return 1


@multifactor_protected(factors=risk_based_factor_count)
def billing(request): ...
```

Typical inputs to the callable:

- Request origin (`request.META["REMOTE_ADDR"]`, geolocation lookup).
- Time of day (after-hours = stricter).
- User attributes (`request.user.is_staff`, group membership).
- Recent security events read from another model.

```{caution}
Anything you read inside `factors=` runs **on every request** to the
decorated view. Keep it fast — a `User.objects.filter(...).count()` is
cheap; a third-party HTTP call is not.
```

## Combining with @login_required

`multifactor_protected` lets unauthenticated requests fall through unchanged.
You almost always want `@login_required` *outside* it:

```python
@login_required
@multifactor_protected(factors=1)
def billing(request): ...
```

Decorator order in Python is bottom-up: `multifactor_protected` runs first,
sees `request.user.is_anonymous`, returns the wrapped view's response —
which `@login_required` then intercepts.

## Protecting class-based views

Use `django.utils.decorators.method_decorator`:

```python
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView


@method_decorator(multifactor_protected(factors=1), name="dispatch")
class Billing(TemplateView):
    template_name = "billing.html"
```

Or use the mixins, which read more naturally for CBVs — see
[Mixins](mixins.md).

## Protecting an entire URL tree

`decorator_include` from
[django-decorator-include](https://pypi.org/project/django-decorator-include/)
wraps every URL inside an `include()`:

```python
from decorator_include import decorator_include
from multifactor.decorators import multifactor_protected

urlpatterns = [
    path("admin/multifactor/", include("multifactor.urls")),
    path(
        "admin/",
        decorator_include(multifactor_protected(factors=1), admin.site.urls),
    ),
]
```

This is the cleanest way to MFA-gate Django admin without modifying admin
source.

## When the decorator doesn't fire

The decorator quietly lets the request through in these cases:

1. `request.user.is_authenticated` is `False` — your auth stack should handle
   this.
2. `is_bypassed(request)` returns truthy — see [conditional bypass](conditional-bypass.md).
3. `user_filter` is set and the user doesn't match.
4. `factors == 0`, the user has no `UserKey` rows, and `advertise=False`.

All other paths end in either "render the wrapped view" or "redirect to
`multifactor:authenticate`".

## See also

- [Mixins](mixins.md) — the class-based-view equivalent.
- [Conditional bypass](conditional-bypass.md) — escape hatches.
- [`multifactor.decorators` reference](../reference/decorators.md) — the docstring/API view.
