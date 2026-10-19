from django.apps import AppConfig
from django.core.checks import Warning, register
from django.utils.translation import gettext_lazy as _


class MultifactorConfig(AppConfig):
    default = True
    name = "multifactor"
    verbose_name = _("Multifactor")
    default_auto_field = "django.db.models.AutoField"

    def ready(self):
        register(check_attempt_cache)


def check_attempt_cache(app_configs=None, **kwargs):
    """Warn when failed-attempt counting is enabled but the cache can't remember anything."""
    from django.conf import settings

    from .app_settings import mf_settings

    backend = settings.CACHES.get("default", {}).get("BACKEND", "")
    if mf_settings["MAX_ATTEMPTS"] and backend.endswith("DummyCache"):
        return [
            Warning(
                "django-multifactor attempt limiting is inactive: the default cache is DummyCache.",
                hint=(
                    "Configure a real cache shared between workers (Redis, Memcached, database), "
                    'or set MULTIFACTOR["MAX_ATTEMPTS"] = 0 and rate-limit the MFA URLs elsewhere.'
                ),
                id="multifactor.W001",
            )
        ]

    return []
