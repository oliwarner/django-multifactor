# Admin integration

`django-multifactor` ships an opinionated `UserAdmin` mixin that surfaces
factor usage in the Django admin. It is purely additive — no behaviour
changes unless you opt in.

## Adding the mixin

```python
# myapp/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model

from multifactor.admin import MultifactorUserAdmin

User = get_user_model()


@admin.register(User)
class StaffUserAdmin(UserAdmin, MultifactorUserAdmin):
    pass
```

After this:

- The user changelist gains a **Multifactor** column (boolean green/red dot)
  showing whether the user has at least one *enabled* factor.
- A **Using Multifactor authentication?** filter appears in the sidebar
  (Yes / No).
- The user detail page gains a read-only inline listing each of the user's
  `UserKey` rows with an enable/disable toggle.

Source: `multifactor/admin.py`.

## Disabling individual pieces

Three class-level flags let you turn parts off:

```python
@admin.register(User)
class StaffUserAdmin(UserAdmin, MultifactorUserAdmin):
    multifactor_list_display = False  # hide the changelist column
    multifactor_filter = False  # hide the sidebar filter
    multifactor_inline = False  # hide the inline on the detail page
```

## Emergency disable: turning off a user's factors

The inline lets an admin **toggle `enabled`** on each key. Disabling a key
makes it stop working immediately:

- `active_factors(request)` doesn't drop the existing session marker, but
  `has_multifactor()` re-checks `enabled=True` on each protected view, so
  the user is challenged on next page load.
- The key is **not deleted**, so an audit trail is preserved.

To completely revoke MFA for a user (e.g. they lost their hardware key and
have no backup, no fallback), an admin can delete the user's `UserKey` rows
via the inline. The user will then have no factors and:

- Will not be challenged on `factors=0` views.
- Will be sent to the **Add factor** page on `RequireMultiAuthMixin` views.
- Will be sent to `multifactor:authenticate` with no available method on
  `factors>=1` views — they need to log in, register a new factor, and try
  again.

## A custom action — disable MFA on selected users

```python
from django.contrib import admin
from multifactor.models import UserKey


@admin.action(description="Disable MFA for selected users")
def disable_mfa(modeladmin, request, queryset):
    UserKey.objects.filter(user__in=queryset).update(enabled=False)


@admin.register(User)
class StaffUserAdmin(UserAdmin, MultifactorUserAdmin):
    actions = [disable_mfa]
```

```{warning}
This is a powerful action. Limit it to a small group of trusted admins
(consider a custom permission) and audit every use.
```

## Showing the count of factors per user

```python
from django.db.models import Count


@admin.register(User)
class StaffUserAdmin(UserAdmin, MultifactorUserAdmin):
    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                factor_count=Count(
                    "multifactor_keys", filter=Q(multifactor_keys__enabled=True)
                ),
            )
        )

    def factor_count(self, obj):
        return obj.factor_count

    factor_count.short_description = "Active factors"
```

Note the `multifactor_keys` related name on the `UserKey.user` ForeignKey
(`models.py:21`).

## Auditing factor registrations

For an audit trail of "who registered which factor when", listen for the
post-save signal on `UserKey`:

```python
# myapp/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from multifactor.models import UserKey


@receiver(post_save, sender=UserKey)
def audit_factor_change(sender, instance, created, **kwargs):
    import logging

    log = logging.getLogger("audit.mfa")
    log.info(
        "userkey %s for user=%s type=%s enabled=%s",
        "created" if created else "updated",
        instance.user_id,
        instance.key_type,
        instance.enabled,
    )
```

Wire that in `apps.ready()`.

## See also

- [Models reference](../reference/models.md) — fields available on `UserKey`.
- [Branding](branding.md) — for theming the user-facing pages.
