from importlib import reload

from django.test import SimpleTestCase, override_settings


class AppSettingsTests(SimpleTestCase):
    def _reload_module(self):
        import multifactor.app_settings as app_settings

        return reload(app_settings)

    @override_settings(MULTIFACTOR={})
    def test_defaults_are_applied(self):
        app_settings = self._reload_module()

        self.assertEqual(
            app_settings.mf_settings["LOGIN_MESSAGE"],
            'You are now multifactor-authenticated. <a href="{}">Multifactor settings</a>.',
        )
        self.assertTrue(app_settings.mf_settings["SHOW_LOGIN_MESSAGE"])
        self.assertFalse(app_settings.mf_settings["LOGIN_CALLBACK"])
        self.assertTrue(app_settings.mf_settings["RECHECK"])
        self.assertEqual(app_settings.mf_settings["RECHECK_MIN"], 60 * 60 * 3)
        self.assertEqual(app_settings.mf_settings["RECHECK_MAX"], 60 * 60 * 6)
        self.assertEqual(app_settings.mf_settings["FIDO_SERVER_ID"], "example.com")
        self.assertEqual(app_settings.mf_settings["FIDO_SERVER_NAME"], "Django App")
        self.assertIsNone(app_settings.mf_settings["FIDO_SERVER_ICON"])
        self.assertEqual(app_settings.mf_settings["TOKEN_ISSUER_NAME"], "Django App")
        self.assertEqual(app_settings.mf_settings["FACTORS"], ["FIDO2", "TOTP"])
        self.assertIn("email", app_settings.mf_settings["FALLBACKS"])
        self.assertEqual(
            app_settings.mf_settings["FALLBACKS"]["email"][1],
            "multifactor.factors.fallback.send_email",
        )
        self.assertTrue(app_settings.mf_settings["HTML_EMAIL"])
        self.assertIsNone(app_settings.mf_settings["BYPASS"])

    @override_settings(MULTIFACTOR={})
    def test_default_email_fallback_uses_user_email(self):
        app_settings = self._reload_module()

        email_getter, sender_path = app_settings.mf_settings["FALLBACKS"]["email"]

        user = type("User", (), {"email": "alice@example.com"})()
        self.assertEqual(email_getter(user), "alice@example.com")
        self.assertEqual(sender_path, "multifactor.factors.fallback.send_email")

    @override_settings(
        MULTIFACTOR={
            "LOGIN_MESSAGE": "custom",
            "SHOW_LOGIN_MESSAGE": False,
            "LOGIN_CALLBACK": "path.to.callback",
            "RECHECK": False,
            "RECHECK_MIN": 10,
            "RECHECK_MAX": 20,
            "FIDO_SERVER_ID": "example.org",
            "FIDO_SERVER_NAME": "Custom App",
            "FIDO_SERVER_ICON": "icon.png",
            "TOKEN_ISSUER_NAME": "Issuer",
            "FACTORS": ["TOTP"],
            "FALLBACKS": {"sms": ("user.phone", "path.to.sms")},
            "HTML_EMAIL": False,
            "BYPASS": "path.to.bypass",
        }
    )
    def test_custom_values_are_preserved(self):
        app_settings = self._reload_module()

        self.assertEqual(app_settings.mf_settings["LOGIN_MESSAGE"], "custom")
        self.assertFalse(app_settings.mf_settings["SHOW_LOGIN_MESSAGE"])
        self.assertEqual(app_settings.mf_settings["LOGIN_CALLBACK"], "path.to.callback")
        self.assertFalse(app_settings.mf_settings["RECHECK"])
        self.assertEqual(app_settings.mf_settings["RECHECK_MIN"], 10)
        self.assertEqual(app_settings.mf_settings["RECHECK_MAX"], 20)
        self.assertEqual(app_settings.mf_settings["FIDO_SERVER_ID"], "example.org")
        self.assertEqual(app_settings.mf_settings["FIDO_SERVER_NAME"], "Custom App")
        self.assertEqual(app_settings.mf_settings["FIDO_SERVER_ICON"], "icon.png")
        self.assertEqual(app_settings.mf_settings["TOKEN_ISSUER_NAME"], "Issuer")
        self.assertEqual(app_settings.mf_settings["FACTORS"], ["TOTP"])
        self.assertEqual(app_settings.mf_settings["FALLBACKS"], {"sms": ("user.phone", "path.to.sms")})
        self.assertFalse(app_settings.mf_settings["HTML_EMAIL"])
        self.assertEqual(app_settings.mf_settings["BYPASS"], "path.to.bypass")
