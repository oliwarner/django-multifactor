from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from multifactor.models import DisabledFallback, KeyTypes, UserKey


class UserKeyModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password123",
        )

    def test_str_uses_name_when_present(self):
        key = UserKey(
            user=self.user,
            name="Work Key",
            key_type=KeyTypes.FIDO2,
            properties={},
        )

        self.assertEqual(
            str(key),
            'FIDO2 Security Device, aka "Work Key" for alice',
        )

    def test_str_without_name(self):
        key = UserKey(
            user=self.user,
            name=None,
            key_type=KeyTypes.TOTP,
            properties={},
        )

        self.assertEqual(
            str(key),
            "TOTP Authenticator for alice",
        )

    def test_display_name_uses_name_when_present(self):
        key = UserKey(
            user=self.user,
            name="Phone",
            key_type=KeyTypes.TOTP,
            properties={},
        )

        self.assertEqual(key.display_name(), "Phone (TOTP)")

    def test_display_name_without_name(self):
        key = UserKey(
            user=self.user,
            name="",
            key_type=KeyTypes.FIDO2,
            properties={},
        )

        self.assertEqual(key.display_name(), "FIDO2 Security Device")

    def test_device_returns_fido2_type(self):
        key = UserKey(
            user=self.user,
            name="Security Key",
            key_type=KeyTypes.FIDO2,
            properties={"type": "YubiKey"},
        )

        self.assertEqual(key.device, "YubiKey")

    def test_device_returns_default_for_fido2_when_type_missing(self):
        key = UserKey(
            user=self.user,
            name="Security Key",
            key_type=KeyTypes.FIDO2,
            properties={},
        )

        self.assertEqual(key.device, "----")

    def test_device_returns_empty_string_for_non_fido2(self):
        key = UserKey(
            user=self.user,
            name="Authenticator",
            key_type=KeyTypes.TOTP,
            properties={},
        )

        self.assertEqual(key.device, "")

    def test_auth_url_delegates_to_method_url(self):
        key = UserKey(
            user=self.user,
            name="Authenticator",
            key_type=KeyTypes.TOTP,
            properties={},
        )
        with patch("multifactor.common.method_url", return_value="/fake-url/") as method_url:
            self.assertEqual(key.auth_url, "/fake-url/")
            method_url.assert_called_once_with(KeyTypes.TOTP)

    def test_disabled_fallback_can_be_saved(self):
        fallback = DisabledFallback.objects.create(
            user=self.user,
            fallback="email",
        )

        self.assertEqual(fallback.user, self.user)
        self.assertEqual(fallback.fallback, "email")