# Logging

`django-multifactor` uses Python's standard `logging` module. Each module
gets a logger named after its dotted path. To see what the package is doing,
configure these loggers in your project's `LOGGING` config.

## What gets logged

| Logger | Emits |
| --- | --- |
| `multifactor.factors.fido2` | `logger.exception("Error completing FIDO2 registration.")` when `register_complete()` raises. Includes the original traceback. |
| `multifactor.factors.fallback` | `logger.exception("Could not send email:", user)` when the email transport raises. |
| `multifactor.factors.totp` | Currently no log emissions — failed verifications return False and surface as `messages.error()`. |

The package is intentionally quiet — it doesn't `info`-log every challenge.
If you need that visibility, hook signals (see [admin integration](../guides/admin-integration.md))
or add log lines in your own middleware.

## Recommended LOGGING config

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "multifactor": {
            "handlers": ["console"],
            "level": "DEBUG",  # tighten to INFO in production
            "propagate": False,
        },
    },
}
```

Send to your central log aggregator the same way you send your other Django
logs.

## Adding your own audit log

For a richer audit trail, hook signals on `UserKey`:

```python
# myapp/audit.py
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from multifactor.models import UserKey

audit = logging.getLogger("audit.mfa")


@receiver(post_save, sender=UserKey)
def factor_saved(sender, instance, created, **kwargs):
    audit.info(
        "%s: user=%s type=%s enabled=%s key_id=%s",
        "created" if created else "updated",
        instance.user_id,
        instance.key_type,
        instance.enabled,
        instance.pk,
    )


@receiver(post_delete, sender=UserKey)
def factor_deleted(sender, instance, **kwargs):
    audit.warning(
        "deleted: user=%s type=%s key_id=%s",
        instance.user_id,
        instance.key_type,
        instance.pk,
    )
```

Wire that into your `AppConfig.ready()` so the signals fire from app start.

## Logging the request flow

To trace why a particular request was challenged (or wasn't), add a logger
in your own middleware that reads `multifactor` session state:

```python
# myapp/middleware.py
import logging

log = logging.getLogger("debug.mfa")


class LogMfaState:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            log.debug(
                "user=%s path=%s mfa_session=%r",
                request.user.pk,
                request.path,
                request.session.get("multifactor"),
            )
        return self.get_response(request)
```

Add to `MIDDLEWARE` **after** `AuthenticationMiddleware`. Remove in
production — this is a debug aid, not an audit log.

## Logging within a custom fallback transport

Custom transports should log on both success and failure. Use the package
convention — a module-level `logger = logging.getLogger(__name__)`:

```python
# myapp/mfa.py
import logging

log = logging.getLogger(__name__)


def send_sms(user, message):
    try:
        # ... twilio call
        log.info("SMS OTP sent: user=%s", user.pk)
        return "sms"
    except Exception:
        log.exception("SMS OTP failed: user=%s", user.pk)
        return False
```

Failures are silently swallowed by the package's dispatch loop (`except:
pass` in `factors/fallback.py:46`) — if you don't log them yourself, you
will never know they happened.

## See also

- [Session debugging](session-debugging.md) — live state inspection.
- [Common issues](common-issues.md).
