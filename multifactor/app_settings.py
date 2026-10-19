from django.conf import settings
from django.utils.translation import gettext_lazy as _

mf_settings = getattr(settings, "MULTIFACTOR", {})

mf_settings["LOGIN_MESSAGE"] = mf_settings.get(
    "LOGIN_MESSAGE", _('You are now multifactor-authenticated. <a href="{}">Multifactor settings</a>.')
)
mf_settings["SHOW_LOGIN_MESSAGE"] = mf_settings.get("SHOW_LOGIN_MESSAGE", True)
mf_settings["LOGIN_CALLBACK"] = mf_settings.get("LOGIN_CALLBACK", False)
mf_settings["RECHECK"] = mf_settings.get("RECHECK", True)
mf_settings["RECHECK_MIN"] = mf_settings.get("RECHECK_MIN", 60 * 60 * 3)
mf_settings["RECHECK_MAX"] = mf_settings.get("RECHECK_MAX", 60 * 60 * 6)

mf_settings["FIDO_SERVER_ID"] = mf_settings.get("FIDO_SERVER_ID", "example.com")
mf_settings["FIDO_SERVER_NAME"] = mf_settings.get("FIDO_SERVER_NAME", "Django App")
mf_settings["FIDO_SERVER_ICON"] = mf_settings.get("FIDO_SERVER_ICON", None)
mf_settings["TOKEN_ISSUER_NAME"] = mf_settings.get("TOKEN_ISSUER_NAME", "Django App")

mf_settings["FACTORS"] = mf_settings.get("FACTORS", ["FIDO2", "TOTP"])

mf_settings["FALLBACKS"] = mf_settings.get(
    "FALLBACKS",
    {
        "email": (lambda user: user.email, "multifactor.factors.fallback.send_email"),
    },
)

mf_settings["HTML_EMAIL"] = mf_settings.get("HTML_EMAIL", True)

mf_settings["BYPASS"] = mf_settings.get("BYPASS", None)

# Number of 30 second TOTP steps either side of "now" that are accepted. 1 is the
# RFC 6238 recommendation (3 valid codes). Raising it trades security for tolerance of
# device clock drift: 60 (the old behaviour) accepts 121 codes, ie +/-30 minutes.
mf_settings["TOTP_WINDOW"] = mf_settings.get("TOTP_WINDOW", 1)

# Failed TOTP / fallback OTP attempts allowed per user within ATTEMPT_PERIOD seconds
# before the user is logged out and further attempts are refused until the period
# expires. Set MAX_ATTEMPTS to 0 to disable. Counters live in Django's cache, so
# production needs a cache shared between workers (Redis, Memcached, database).
mf_settings["MAX_ATTEMPTS"] = mf_settings.get("MAX_ATTEMPTS", 5)
mf_settings["ATTEMPT_PERIOD"] = mf_settings.get("ATTEMPT_PERIOD", 60 * 5)
