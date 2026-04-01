from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase

from multifactor.factors.fallback import SESSION_KEY, SESSION_KEY_SUCCEEDED
from multifactor.models import DisabledFallback


class FallbackTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password123",
        )
        self.client.force_login(self.user)

    @patch("multifactor.factors.fallback.import_string")
    @patch("multifactor.factors.fallback.disabled_fallbacks", return_value=[])
    def test_get_generates_otp_and_calls_transports(self, disabled_fallbacks, import_string):
        transport = lambda user, message: "email"
        import_string.return_value = transport

        response = self.client.get("/admin/multifactor/fallback/auth/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(SESSION_KEY, self.client.session)
        self.assertIn(SESSION_KEY_SUCCEEDED, self.client.session)

    def test_post_with_matching_otp_logs_in(self):
        session = self.client.session
        session[SESSION_KEY] = "123456"
        session[SESSION_KEY_SUCCEEDED] = "email"
        session.save()

        with patch("multifactor.factors.fallback.write_session") as write_session, \
                patch("multifactor.factors.fallback.login") as login:
            login.return_value = HttpResponse()
            response = self.client.post("/admin/multifactor/fallback/auth/", {"otp": "123456"})

        self.assertEqual(response.status_code, 200)
        write_session.assert_called_once()
        login.assert_called_once()

    def test_post_with_bad_otp_shows_error(self):
        session = self.client.session
        session[SESSION_KEY] = "123456"
        session[SESSION_KEY_SUCCEEDED] = "email"
        session.save()

        with patch("multifactor.factors.fallback.messages.error") as msg_error:
            response = self.client.post("/admin/multifactor/fallback/auth/", {"otp": "000000"})

        self.assertEqual(response.status_code, 200)
        msg_error.assert_called_once()

    def test_disabled_fallback_round_trip(self):
        DisabledFallback.objects.create(user=self.user, fallback="email")
        self.assertEqual(DisabledFallback.objects.filter(user=self.user).count(), 1)