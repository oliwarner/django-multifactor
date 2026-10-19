import importlib
from unittest.mock import patch

from django.test import SimpleTestCase


class InitTests(SimpleTestCase):
    @patch("django.VERSION", (3, 1))
    def test_default_app_config_is_set_on_old_django(self):
        module = importlib.import_module("multifactor")
        importlib.reload(module)
        self.assertEqual(module.default_app_config, "multifactor.apps.MultifactorConfig")

    @patch("django.VERSION", (3, 2))
    def test_default_app_config_is_not_set_on_newer_django(self):
        module = importlib.import_module("multifactor")
        importlib.reload(module)
        self.assertFalse(hasattr(module, "default_app_config"))


class LockoutPeriodCheckTests(SimpleTestCase):
    def run_check(self, **overrides):
        from multifactor.checks import check_lockout_period

        with patch.dict("multifactor.app_settings.mf_settings", overrides):
            return check_lockout_period()

    def test_warns_when_lockout_is_shorter_than_attempt_period(self):
        warnings = self.run_check(ATTEMPT_PERIOD=300, LOCKOUT_PERIOD=60)

        self.assertEqual([w.id for w in warnings], ["multifactor.W001"])

    def test_silent_when_lockout_equals_attempt_period(self):
        self.assertEqual(self.run_check(ATTEMPT_PERIOD=300, LOCKOUT_PERIOD=300), [])

    def test_silent_with_the_defaults(self):
        self.assertEqual(self.run_check(ATTEMPT_PERIOD=300, LOCKOUT_PERIOD=1800), [])

    def test_silent_when_attempt_limiting_is_disabled(self):
        self.assertEqual(self.run_check(MAX_ATTEMPTS=0, ATTEMPT_PERIOD=300, LOCKOUT_PERIOD=60), [])

    def test_check_is_registered(self):
        from django.core.checks import registry

        from multifactor.checks import check_lockout_period

        self.assertIn(check_lockout_period, registry.registry.registered_checks)
