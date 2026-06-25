# multifactor.mixins

```python
from multifactor.mixins import (
    MultiFactorMixin,
    RequireMultiAuthMixin,
    PreferMultiAuthMixin,
)
```

Class-based view mixins. None of these accept any configuration — they are
"all or nothing" relative to the decorator. Source: `multifactor/mixins.py`.

## MultiFactorMixin

Annotates `self` with multifactor state during `setup()`. **Does not redirect**.
Use when you want to read MFA state from your view code or template (e.g. to
render a "you're using MFA" badge) without enforcing it.

### Attributes set on `self`

| Attribute | Type | Meaning |
| --- | --- | --- |
| `active_factors` | `list[tuple]` | The list of currently-verified factors in `request.session["multifactor"]`, with expired entries filtered. |
| `factors` | `QuerySet[UserKey]` | All `UserKey` rows for the current user, enabled or not. |
| `has_multifactor` | `bool` | `True` if the user has at least one **enabled** `UserKey`. |
| `bypass` | `bool` | The return value of `is_bypassed(request)`. |

Only set when `request.user.is_authenticated`. For anonymous requests these
attributes are absent — `super().setup()` returns early.

## RequireMultiAuthMixin

Inherits from `MultiFactorMixin`. Overrides `dispatch()` to **force MFA**:

- If the user has factors but none active → redirect to `multifactor:authenticate`.
- If the user has no factors at all → redirect to `multifactor:add` (the
  enrolment page).
- If bypass is truthy → view runs unchanged.

Set `request.session["multifactor-next"]` to the original URL so the user
returns after enrolling/authenticating.

This is the **strictest** mixin — use it when you want to force enrolment.

## PreferMultiAuthMixin

Inherits from `MultiFactorMixin`. Overrides `dispatch()` to challenge only
if the user already has factors:

- If the user has factors but none active → redirect to `multifactor:authenticate`.
- If the user has no factors → view runs unchanged.
- If bypass is truthy → view runs unchanged.

Equivalent in effect to `@multifactor_protected(factors=0)` but reads more
naturally in CBV stacks.

## Example — read-only annotation

```python
from django.views.generic import TemplateView
from multifactor.mixins import MultiFactorMixin


class Dashboard(MultiFactorMixin, TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["mfa_active"] = bool(getattr(self, "active_factors", None))
        ctx["mfa_enrolled"] = getattr(self, "has_multifactor", False)
        return ctx
```

## Example — force enrolment

```python
from django.views.generic import TemplateView
from multifactor.mixins import RequireMultiAuthMixin


class AdminConsole(RequireMultiAuthMixin, TemplateView):
    template_name = "admin/console.html"
```

## See also

- [Guide: mixins](../guides/mixins.md) — narrative version.
- [Decorators reference](decorators.md) — function-style alternative.
