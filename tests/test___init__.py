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


class AttemptCacheCheckTests(SimpleTestCase):
    DUMMY = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
    LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

    def run_check(self):
        from multifactor.apps import check_attempt_cache

        return check_attempt_cache()

    def test_warns_when_cache_is_dummy(self):
        with self.settings(CACHES=self.DUMMY):
            self.assertEqual([w.id for w in self.run_check()], ["multifactor.W001"])

    def test_silent_with_a_real_cache(self):
        with self.settings(CACHES=self.LOCMEM):
            self.assertEqual(self.run_check(), [])

    def test_silent_when_attempt_limiting_disabled(self):
        with self.settings(CACHES=self.DUMMY), patch.dict("multifactor.app_settings.mf_settings", {"MAX_ATTEMPTS": 0}):
            self.assertEqual(self.run_check(), [])
