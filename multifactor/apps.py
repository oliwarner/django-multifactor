from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MultifactorConfig(AppConfig):
    default = True
    name = "multifactor"
    verbose_name = _("Multifactor")
    default_auto_field = "django.db.models.AutoField"

    def ready(self):
        from . import checks  # noqa: F401  (registers the system checks)
