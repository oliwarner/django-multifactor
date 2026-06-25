# Class-based view mixins

For class-based views, three mixins live in `multifactor.mixins`. They sit
alongside the `@multifactor_protected` decorator and offer slightly different
semantics — they are *not* a one-to-one replacement.

## The three mixins

| Mixin | Behaviour |
| --- | --- |
| `MultiFactorMixin` | Annotates `self` with `active_factors`, `factors`, `has_multifactor`, `bypass` so your view code can consult them. Does **not** force MFA. |
| `RequireMultiAuthMixin` | "Hard" mode. If the user is not currently MFA-authenticated, they are redirected — to `multifactor:authenticate` if they have factors, or to `multifactor:add` if they don't. **Forces enrolment** on users without factors. |
| `PreferMultiAuthMixin` | "Soft" mode. If the user already has factors, they must be MFA-authenticated. If they have no factors, the view runs normally. |

Source: `multifactor/mixins.py`.

## Choosing between decorator and mixin

| Need | Decorator | Mixin |
| --- | --- | --- |
| "Require N factors" | `@multifactor_protected(factors=N)` | No direct equivalent — mixins do not understand factor counts. |
| "Require any factor if user has factors" | `@multifactor_protected(factors=0)` | `PreferMultiAuthMixin` |
| "Force users to enrol now" | Not directly supported. | `RequireMultiAuthMixin` (redirects to `multifactor:add`). |
| `max_age`, `user_filter`, dynamic `factors` | Yes. | No. |
| Annotate `self` for use inside your view code | No. | `MultiFactorMixin`. |

Rule of thumb: **prefer the decorator** unless you need the enrol-forcing
behaviour of `RequireMultiAuthMixin`, or unless you want `self.active_factors`
visible from inside template/context code.

## Examples

### Read-only annotation — show different UI for MFA users

```python
from django.views.generic import TemplateView
from multifactor.mixins import MultiFactorMixin


class Dashboard(MultiFactorMixin, TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["mfa_active"] = bool(self.active_factors)
        ctx["mfa_enrolled"] = self.has_multifactor
        return ctx
```

The view runs whether or not the user is MFA-authenticated; you can render
a "you're using MFA" badge in the template based on the flags.

### Force enrolment for staff

```python
from django.views.generic import TemplateView
from multifactor.mixins import RequireMultiAuthMixin


class AdminConsole(RequireMultiAuthMixin, TemplateView):
    template_name = "admin/console.html"
```

A staff user hitting this view who has **no** factors registered is sent to
the **Add factor** page. They are then required to enrol before they can
proceed. This is opinionated and aggressive — useful for ops dashboards
where you've decided "no MFA, no access".

### Soft prefer — never block, but challenge if enrolled

```python
from django.views.generic import TemplateView
from multifactor.mixins import PreferMultiAuthMixin


class AccountSettings(PreferMultiAuthMixin, TemplateView):
    template_name = "account.html"
```

Users with factors are challenged. Users without factors are let through.
Equivalent to `@multifactor_protected(factors=0)` but cleaner on CBVs.

## What the mixins do not do

- They do **not** check `max_age`. If you need timing, use the decorator or
  read `active_factors` inside `dispatch()` yourself.
- They do **not** support a callable factor count.
- They do **not** integrate `user_filter` — either subclass and override
  `dispatch`, or use the decorator instead.

## Combining a mixin with the decorator

It is legal (and occasionally useful) to use both:

```python
from django.utils.decorators import method_decorator


@method_decorator(multifactor_protected(factors=2, max_age=300), name="dispatch")
class HighValue(PreferMultiAuthMixin, TemplateView):
    template_name = "transfer.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["last_verified"] = (
            self.active_factors[0][2] if self.active_factors else None
        )
        return ctx
```

The decorator enforces the factor count and age; the mixin gives the template
visibility into `active_factors`.

## See also

- [Protecting views](protecting-views.md) — the decorator equivalent.
- [`multifactor.mixins` reference](../reference/mixins.md) — full API.
