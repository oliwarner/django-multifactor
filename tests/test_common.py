from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings

from multifactor.common import (
    active_factors,
    has_multifactor,
    is_bypassed,
    login,
    method_url,
    next_check,
    render,
    write_session,
)
from multifactor.models import KeyTypes, UserKey


class CommonTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password123",
        )

    def _request(self, path="/"):
        request = self.factory.get(path)
        request.user = self.user
        request.session = {}
        return request

    @override_settings(MULTIFACTOR={"RECHECK_MIN": 10, "RECHECK_MAX": 10})
    @patch("multifactor.common.random.randint", return_value=10)
    @patch("multifactor.common.timezone.now")
    def test_next_check_uses_recheck_window(self, now, randint):
        now.return_value.timestamp.return_value = 100

        self.assertEqual(next_check(), 110)
        randint.assert_called_once_with(10, 10)

    def test_method_url_lowercases_method_name(self):
        self.assertEqual(method_url("TOTP"), "multifactor:totp_auth")
        self.assertEqual(method_url("FIDO2"), "multifactor:fido2_auth")

    def test_render_passes_context_through(self):
        request = self._request()

        with patch("multifactor.common.dj_render", return_value=HttpResponse("ok")) as dj_render:
            response = render(request, "template.html", {"a": 1}, status=201)

        self.assertEqual(response.status_code, 200)
        dj_render.assert_called_once()
        self.assertEqual(dj_render.call_args.args[1], "template.html")
        self.assertEqual(dj_render.call_args.args[2], {"a": 1})
        self.assertEqual(dj_render.call_args.kwargs["status"], 201)

    def test_has_multifactor_true_when_enabled_key_exists(self):
        UserKey.objects.create(
            user=self.user,
            key_type=KeyTypes.TOTP,
            properties={},
            enabled=True,
        )
        request = self._request()

        self.assertTrue(has_multifactor(request))

    def test_has_multifactor_false_when_only_disabled_key_exists(self):
        UserKey.objects.create(
            user=self.user,
            key_type=KeyTypes.TOTP,
            properties={},
            enabled=False,
        )
        request = self._request()

        self.assertFalse(has_multifactor(request))

    def test_active_factors_filters_expired_entries(self):
        request = self._request()
        request.session["multifactor"] = [
            ("TOTP", 1, 50, 60),
            ("TOTP", 2, 50, False),
            ("TOTP", 3, 50, 999),
        ]

        with patch("multifactor.common.timezone.now") as now:
            now.return_value.timestamp.return_value = 100
            factors = active_factors(request)

        self.assertEqual(factors, [
            ("TOTP", 2, 50, False),
            ("TOTP", 3, 50, 999),
        ])
        self.assertEqual(request.session["multifactor"], factors)

    @override_settings(MULTIFACTOR={"SHOW_LOGIN_MESSAGE": True, "LOGIN_MESSAGE": 'Logged in via {}'})
    def test_login_with_next_redirects_and_pops_session(self):
        request = self._request()
        request.session["multifactor-next"] = "/target/"
        request.session["base_username"] = "alice"

        with patch("multifactor.common.messages.info") as msg_info:
            response = login(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/target/")
        self.assertNotIn("multifactor-next", request.session)
        msg_info.assert_called_once()

    @override_settings(MULTIFACTOR={"SHOW_LOGIN_MESSAGE": False, "LOGIN_CALLBACK": False})
    def test_login_without_next_redirects_to_login_url(self):
        request = self._request()

        with patch("multifactor.common.settings.LOGIN_URL", "/login/"):
            response = login(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/login/")

    @override_settings(MULTIFACTOR={"LOGIN_CALLBACK": "path.to.callback"})
    def test_login_uses_callback_when_configured(self):
        request = self._request()
        request.session["base_username"] = "alice"

        callback = MagicMock(return_value=HttpResponse("callback"))
        with patch("multifactor.common.import_string", return_value=callback):
            response = login(request)

        callback.assert_called_once_with(request, username="alice")
        self.assertEqual(response.status_code, 200)

    @override_settings(MULTIFACTOR={"BYPASS": "path.to.bypass"})
    def test_is_bypassed_uses_callback(self):
        request = self._request()

        with patch("multifactor.common.import_string", return_value=lambda req: True) as imp:
            self.assertTrue(is_bypassed(request))

        imp.assert_called_once_with("path.to.bypass")

    @override_settings(MULTIFACTOR={"BYPASS": None})
    def test_is_bypassed_returns_false_when_unconfigured(self):
        request = self._request()
        self.assertFalse(is_bypassed(request))

    @override_settings(MULTIFACTOR={"RECHECK": True, "RECHECK_MIN": 60, "RECHECK_MAX": 60})
    @patch("multifactor.common.next_check", return_value=999)
    @patch("multifactor.common.timezone.now")
    def test_write_session_saves_key_and_updates_last_used(self, now, next_check_mock):
        request = self._request()
        key = UserKey.objects.create(
            user=self.user,
            key_type=KeyTypes.TOTP,
            properties={},
        )
        now.return_value.timestamp.return_value = 123
        now.return_value = now.return_value

        write_session(request, key)

        self.assertEqual(request.session["multifactor"][0][0], "TOTP")
        self.assertEqual(request.session["multifactor"][0][1], key.id)
        self.assertEqual(request.session["multifactor"][0][2], 123)
        self.assertEqual(request.session["multifactor"][0][3], 999)
        key.refresh_from_db()
        self.assertIsNotNone(key.last_used)

    @override_settings(MULTIFACTOR={"RECHECK": False})
    @patch("multifactor.common.timezone.now")
    def test_write_session_without_key_stores_false_recheck(self, now):
        request = self._request()
        now.return_value.timestamp.return_value = 123

        write_session(request, None)

        self.assertEqual(request.session["multifactor"][0], (None, None, 123, False))