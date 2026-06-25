# multifactor.decorators

```python
from multifactor.decorators import multifactor_protected
```

The single public symbol in `multifactor.decorators`.

## multifactor_protected

```text
multifactor_protected(
    factors: int | Callable[[HttpRequest], int] = 0,
    user_filter: dict | None = None,
    max_age: int = 0,
    advertise: bool = False,
)
```

Decorator factory. Returns a decorator that wraps a view function.

### Parameters

| Name | Type | Effect |
| --- | --- | --- |
| `factors` | `int` or `Callable[[HttpRequest], int]` | Minimum number of *active* (verified-and-not-expired) factors required for the view to render. `0` means "challenge only users who already have factors registered". When callable, called with the request on every invocation — keep it fast. |
| `user_filter` | `dict \| None` | Passed verbatim to `User.objects.filter(pk=request.user.pk, **user_filter)`. Users not matching are let through without challenge. `None` matches everyone. |
| `max_age` | `int` (seconds) | Seconds since the most recent factor's `verified_at`. `0` disables the timing check (rely on `RECHECK` instead). |
| `advertise` | `bool` | When `factors=0` and the user has *no* factors yet, show a one-off `messages.info()` banner with a link to the manage-factors page. Persists across the session via `session["multifactor-advertised"]`. |

### Returns

A decorator suitable for function views, or — via
`django.utils.decorators.method_decorator` — class-based view methods.

### Behaviour matrix

| Request state | `factors` int | `factors` callable | Action |
| --- | --- | --- | --- |
| User not authenticated | any | any | View runs unchanged (your auth stack handles it). |
| `is_bypassed(request)` truthy | any | any | View runs unchanged. |
| `user_filter` set, user doesn't match | any | any | View runs unchanged. |
| Active factors >= required | met | met | View runs unchanged. |
| User has keys but none active | any | any | Redirect to `multifactor:authenticate`. |
| `max_age` elapsed | any | any | Flash warning, redirect to `multifactor:authenticate`. |
| Active factors < required (with `factors>=1`) | unmet | unmet | Flash warning, redirect to `multifactor:authenticate`. |
| `factors=0`, no keys, `advertise=False` | met | met | View runs unchanged. |
| `factors=0`, no keys, `advertise=True` | met | met | View runs; flash one-off info banner. |

### Example — function view

```python
from django.contrib.auth.decorators import login_required
from multifactor.decorators import multifactor_protected


@login_required
@multifactor_protected(factors=1, max_age=30 * 60, user_filter={"is_staff": True})
def admin_dashboard(request): ...
```

### Example — class-based view

```python
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from multifactor.decorators import multifactor_protected


@method_decorator(multifactor_protected(factors=1), name="dispatch")
class Billing(TemplateView):
    template_name = "billing.html"
```

### Example — entire URL tree

```python
from decorator_include import decorator_include
from multifactor.decorators import multifactor_protected

urlpatterns = [
    path(
        "admin/",
        decorator_include(multifactor_protected(factors=1), admin.site.urls),
    ),
]
```

## See also

- [Guide: protecting views](../guides/protecting-views.md) — narrative version.
- [Mixins reference](mixins.md) — class-based alternative.
- Source: `multifactor/decorators.py`.
