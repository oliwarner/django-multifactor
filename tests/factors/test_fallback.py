from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase, override_settings

from multifactor.factors.fallback import (
    SESSION_KEY,
    SESSION_KEY_SUCCEEDED,
    Auth,
    debug_print_console,
    send_email,
)
from multifactor.models import AuthAttempt, DisabledFallback


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

        with patch("multifactor.factors.fallback.write_session") as write_session, patch(
            "multifactor.factors.fallback.login"
        ) as login:
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

    @patch("multifactor.factors.fallback.mf_settings", {"FALLBACKS": {}})
    def test_route_is_404_when_no_fallbacks_configured(self):
        url = "/admin/multifactor/fallback/auth/"

        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertNotIn(SESSION_KEY, self.client.session)

        session = self.client.session
        session[SESSION_KEY] = "12345678"
        session.save()
        self.assertEqual(self.client.post(url, {"otp": "12345678"}).status_code, 404)
        self.assertFalse(self.client.session.get("multifactor"))

    @patch("multifactor.factors.fallback.import_string", return_value=lambda user, message: False)
    @patch("multifactor.factors.fallback.disabled_fallbacks", return_value=[])
    def test_otp_is_not_kept_when_no_transport_delivered_it(self, disabled_fallbacks, import_string):
        response = self.client.get("/admin/multifactor/fallback/auth/")

        self.assertEqual(response.status_code, 302)
        self.assertNotIn(SESSION_KEY, self.client.session)

    @patch("multifactor.factors.fallback.import_string", return_value=lambda user, message: "email")
    @patch("multifactor.factors.fallback.disabled_fallbacks", return_value=[])
    def test_generated_otp_is_eight_digits(self, disabled_fallbacks, import_string):
        self.client.get("/admin/multifactor/fallback/auth/")

        otp = self.client.session[SESSION_KEY]
        self.assertEqual(len(otp), 8)
        self.assertTrue(otp.isdigit())

    def test_post_without_a_generated_otp_is_not_an_error(self):
        response = self.client.post("/admin/multifactor/fallback/auth/", {"otp": "12345678"})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.client.session.get("multifactor"))

    def test_post_without_otp_field_is_a_failure_not_an_error(self):
        session = self.client.session
        session[SESSION_KEY] = "12345678"
        session[SESSION_KEY_SUCCEEDED] = "email"
        session.save()

        response = self.client.post("/admin/multifactor/fallback/auth/", {})

        self.assertEqual(response.status_code, 200)

    @patch.dict("multifactor.throttle.mf_settings", {"MAX_ATTEMPTS": 3})
    def test_lockout_after_max_failures_invalidates_otp_and_logs_out(self):
        session = self.client.session
        session[SESSION_KEY] = "12345678"
        session[SESSION_KEY_SUCCEEDED] = "email"
        session.save()
        url = "/admin/multifactor/fallback/auth/"

        with self.assertLogs("multifactor.throttle", level="WARNING"):
            self.assertEqual(self.client.post(url, {"otp": "00000000"}).status_code, 200)
            self.assertEqual(self.client.post(url, {"otp": "00000000"}).status_code, 200)
            locked = self.client.post(url, {"otp": "00000000"})

        self.assertEqual(locked.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

    @patch.dict("multifactor.throttle.mf_settings", {"MAX_ATTEMPTS": 2})
    def test_locked_user_cannot_pass_with_the_correct_otp(self):
        url = "/admin/multifactor/fallback/auth/"

        with self.assertLogs("multifactor.throttle", level="WARNING"):
            for _ in range(2):
                session = self.client.session
                session[SESSION_KEY] = "12345678"
                session[SESSION_KEY_SUCCEEDED] = "email"
                session.save()
                self.client.post(url, {"otp": "00000000"})

            self.client.force_login(self.user)
            session = self.client.session
            session[SESSION_KEY] = "12345678"
            session.save()
            response = self.client.post(url, {"otp": "12345678"})

        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

    @patch.dict("multifactor.throttle.mf_settings", {"MAX_ATTEMPTS": 2})
    def test_failures_are_shared_with_totp(self):
        AuthAttempt.objects.create(user=self.user, factor="TOTP", outcome="failure")  # one failed TOTP attempt
        session = self.client.session
        session[SESSION_KEY] = "12345678"
        session[SESSION_KEY_SUCCEEDED] = "email"
        session.save()

        with self.assertLogs("multifactor.throttle", level="WARNING"):
            response = self.client.post("/admin/multifactor/fallback/auth/", {"otp": "00000000"})

        self.assertEqual(response.status_code, 302)  # locked out on the first fallback failure

    def test_disabled_fallback_round_trip(self):
        DisabledFallback.objects.create(user=self.user, fallback="email")
        self.assertEqual(DisabledFallback.objects.filter(user=self.user).count(), 1)

    @override_settings(SERVER_EMAIL="noreply@example.com", MULTIFACTOR={"HTML_EMAIL": False})
    @patch("multifactor.factors.fallback.mf_settings", {"HTML_EMAIL": False})
    @patch("multifactor.factors.fallback.EmailMultiAlternatives")
    def test_send_email_plain_text_only(self, email_cls):
        email = email_cls.return_value
        email.send.return_value = 1

        result = send_email(self.user, "Hello")

        self.assertEqual(result, "email")
        email.attach_alternative.assert_not_called()

    @patch("multifactor.factors.fallback.logger.exception")
    @patch("multifactor.factors.fallback.EmailMultiAlternatives", side_effect=Exception("boom"))
    def test_send_email_handles_errors(self, email_cls, logger_exception):
        self.assertFalse(send_email(self.user, "Hello"))
        logger_exception.assert_called_once()

    def test_debug_print_console_returns_marker(self):
        self.assertEqual(debug_print_console(self.user, "Hello"), "command line")

    def test_auth_get_without_any_transport_redirects_home(self):
        request = self.client.request().wsgi_request
        request.user = self.user
        request.session = {}

        view = Auth()
        view.setup(request)

        with patch("multifactor.factors.fallback.disabled_fallbacks", return_value=[]), patch(
            "multifactor.factors.fallback.import_string", side_effect=Exception("bad transport")
        ), patch("multifactor.factors.fallback.messages.error") as msg_error:
            response = view.get(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/multifactor/")
        msg_error.assert_called_once()

    def test_auth_get_no_transports_redirects_home(self):
        request = self.client.request().wsgi_request
        request.user = self.user
        request.session = {}

        view = Auth()
        view.setup(request)

        with patch("multifactor.factors.fallback.disabled_fallbacks", return_value=[]), patch(
            "multifactor.factors.fallback.mf_settings", {"FALLBACKS": {}}
        ), patch("multifactor.factors.fallback.messages.error") as msg_error:
            response = view.get(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/multifactor/")
        msg_error.assert_called_once()
