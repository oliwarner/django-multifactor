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