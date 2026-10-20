from django.core.checks import Warning, register


@register()
def check_lockout_period(app_configs=None, **kwargs):
    """Warn when LOCKOUT_PERIOD is shorter than ATTEMPT_PERIOD.

    The failures that cause a lockout would still be inside the attempt window when it ends,
    so a single new failure would lock the user out again straight away.
    """
    from .app_settings import mf_settings

    if mf_settings["MAX_ATTEMPTS"] and mf_settings["LOCKOUT_PERIOD"] < mf_settings["ATTEMPT_PERIOD"]:
        return [
            Warning(
                "MULTIFACTOR['LOCKOUT_PERIOD'] is shorter than MULTIFACTOR['ATTEMPT_PERIOD'].",
                hint=(
                    "After a lockout ends, one more failed attempt will lock the user out again. "
                    "Set LOCKOUT_PERIOD to at least ATTEMPT_PERIOD."
                ),
                id="multifactor.W001",
            )
        ]

    return []
