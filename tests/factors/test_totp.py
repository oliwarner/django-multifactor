from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import reverse

from multifactor.models import KeyTypes, UserKey


@override_settings(
    ROOT_URLCONF="testsite.testsite.urls",
    MULTIFACTOR={"TOKEN_ISSUER_NAME": "Django App"},
)
class TOTPTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password123",
        )
        self.client.force_login(self.user)

    @patch("multifactor.factors.totp.pyotp.random_base32", return_value="SECRET123")
    @patch("multifactor.factors.totp.pyotp.TOTP")
    def test_create_post_success(self, totp_cls, random_base32):
        totp = MagicMock()
        totp.verify.return_value = True
        totp_cls.return_value = totp

        with patch("multifactor.factors.totp.write_session") as write_session, patch(
            "multifactor.factors.totp.messages.success"
        ) as msg_success:
            response = self.client.post(reverse("multifactor:totp_start"), {"answer": "123456"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("multifactor:home"))
        self.assertTrue(UserKey.objects.filter(user=self.user, key_type=KeyTypes.TOTP).exists())
        write_session.assert_called_once()
        msg_success.assert_called_once()

    @patch("multifactor.factors.totp.pyotp.random_base32", return_value="SECRET123")
    @patch("multifactor.factors.totp.pyotp.TOTP")
    def test_create_post_failure(self, totp_cls, random_base32):
        totp = MagicMock()
        totp.verify.return_value = False
        totp_cls.return_value = totp

        with patch("multifactor.factors.totp.messages.error") as msg_error:
            response = self.client.post(reverse("multifactor:totp_start"), {"answer": "000000"})

        self.assertEqual(response.status_code, 200)
        msg_error.assert_called_once()

    def test_auth_post_success(self):
        UserKey.objects.create(
            user=self.user,
            key_type=KeyTypes.TOTP,
            properties={"secret_key": "SECRET123"},
        )

        with patch("multifactor.factors.totp.pyotp.TOTP") as totp_cls, patch(
            "multifactor.factors.totp.write_session"
        ) as write_session, patch("multifactor.factors.totp.login") as login:
            login.return_value = HttpResponse()
            totp = MagicMock()
            totp.verify.return_value = True
            totp_cls.return_value = totp

            response = self.client.post(reverse("multifactor:totp_auth"), {"answer": "123456"})

        self.assertEqual(response.status_code, 200)
        write_session.assert_called_once()
        login.assert_called_once()

    def test_auth_post_failure(self):
        with patch("multifactor.factors.totp.messages.error") as msg_error:
            response = self.client.post(reverse("multifactor:totp_auth"), {"answer": "000000"})

        self.assertEqual(response.status_code, 200)
        msg_error.assert_called_once()
