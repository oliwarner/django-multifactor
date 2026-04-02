from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase, override_settings

from multifactor.factors.fallback import Auth, SESSION_KEY, SESSION_KEY_SUCCEEDED, debug_print_console, send_email
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

    @override_settings(SERVER_EMAIL="noreply@example.com", MULTIFACTOR={"HTML_EMAIL": False})
    @patch("multifactor.factors.fallback.EmailMultiAlternatives")
    def test_send_email_plain_text_only(self, email_cls):
        email = email_cls.return_value
        email.send.return_value = 1

        result = send_email(self.user, "Hello")

        self.assertEqual(result, "email")
        email.attach_alternative.assert_not_called()

    @patch("multifactor.factors.fallback.EmailMultiAlternatives", side_effect=Exception("boom"))
    def test_send_email_handles_errors(self, email_cls):
        self.assertFalse(send_email(self.user, "Hello"))

    def test_debug_print_console_returns_marker(self):
        self.assertEqual(debug_print_console(self.user, "Hello"), "command line")

    def test_auth_get_without_any_transport_redirects_home(self):
        request = self.client.request().wsgi_request
        request.user = self.user
        request.session = {}

        view = Auth.as_view()

        with patch("multifactor.factors.fallback.disabled_fallbacks", return_value=[]), \
             patch("multifactor.factors.fallback.import_string", side_effect=Exception("bad transport")), \
             patch("multifactor.factors.fallback.messages.error") as msg_error:
            response = view(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/multifactor/")
        msg_error.assert_called_once()