from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.shortcuts import reverse
from django.test import RequestFactory, TestCase
from django.utils.html import format_html

from multifactor.models import DisabledFallback, KeyTypes, UserKey
from multifactor.views import Add, Authenticate, Help, List, Rename


class ViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password123",
        )

    def _request(self, path="/admin/multifactor/"):
        request = self.factory.get(path)
        request.user = self.user
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    @patch("multifactor.views.disabled_fallbacks", return_value=[])
    @patch("multifactor.views.mf_settings", {"FALLBACKS": {"email": (lambda u: u.email, "x")}})
    def test_list_context_includes_available_fallbacks(self, disabled_fallbacks):
        request = self._request()
        view = List()
        view.request = request
        view.object = None
        view.has_multifactor = False
        view.active_factors = []
        view.factors = UserKey.objects.none()

        context = view.get_context_data()

        self.assertIn("available_fallbacks", context)
        self.assertEqual(context["can_edit"], True)

    def test_help_template_name(self):
        self.assertEqual(Help.template_name, "multifactor/help.html")

    def test_add_context_lists_all_methods(self):
        request = self._request("/admin/multifactor/add/")
        view = Add()
        view.request = request
        view.object = None

        context = view.get_context_data()

        self.assertIn("methods", context)
        self.assertTrue(context["methods"])

    @patch("multifactor.views.messages")
    def test_get_context_data_triggers_warning_message(self, mocked_messages):
        with patch("multifactor.mixins.active_factors", return_value=[]):
            request = self._request("/admin/multifactor/add/")
            view = List()
            view.request = request
            view.has_multifactor = True
            view.active_factors = []
            view.factors = UserKey.objects.none()
            view.object = None

            context = view.get_context_data()

        self.assertIn("factors", context)
        self.assertIn("authed_kids", context)
        self.assertIn("can_edit", context)
        self.assertIn("available_fallbacks", context)
        self.assertFalse(context["can_edit"])

        mocked_messages.warning.assert_called_once()
        mocked_messages.warning.assert_called_with(
            request,
            format_html(
                "You will not be able to change these settings or add new "
                'factors until until you <a href="{}" class="alert-link">authenticate</a> with '
                "one of your existing secondary factors.",
                reverse("multifactor:authenticate"),
            ),
        )

    def test_list_get_redirects_next_when_already_authenticated(self):
        request = self._request()
        request.session["multifactor-next"] = "/go/"

        UserKey.objects.create(
            user=self.user,
            key_type=KeyTypes.TOTP,
            properties={},
            enabled=True,
        )

        with patch("multifactor.mixins.active_factors", return_value=[("k1", "TOTP")]), patch(
            "multifactor.mixins.is_bypassed", return_value=False
        ):
            response = List.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/go/")

    def test_list_get_redirects_to_add_when_no_keys(self):
        request = self._request()
        request.session["multifactor-next"] = "/go/"

        with patch("multifactor.mixins.active_factors", return_value=[]), patch(
            "multifactor.mixins.is_bypassed", return_value=False
        ), patch("multifactor.mixins.UserKey.objects.filter") as filter_mock:
            filter_mock.return_value.filter.return_value.exists.return_value = False
            response = List.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/multifactor/add/")

    def test_list_post_toggle_factor(self):
        key = UserKey.objects.create(
            user=self.user,
            key_type=KeyTypes.TOTP,
            properties={},
            enabled=True,
        )
        request = self._request("/admin/multifactor/")
        request.method = "POST"
        request.POST = {}
        request.user = self.user

        view = List()
        view.request = request
        view.object = None
        view.factors = UserKey.objects.filter(user=self.user)

        with patch.object(view, "action_toggle_factor") as action:
            response = view.post(request, "toggle_factor", key.pk)

        self.assertEqual(response.status_code, 302)
        action.assert_called_once()

    def test_list_post_delete_factor(self):
        key = UserKey.objects.create(
            user=self.user,
            key_type=KeyTypes.TOTP,
            properties={},
            enabled=True,
        )
        request = self._request("/admin/multifactor/")
        request.method = "POST"
        request.POST = {}
        request.user = self.user

        view = List()
        view.request = request
        view.object = None
        view.factors = UserKey.objects.filter(user=self.user)

        with patch.object(view, "action_delete_factor") as action:
            response = view.post(request, "delete_factor", key.pk)

        self.assertEqual(response.status_code, 302)
        action.assert_called_once()

    def test_list_post_invalid_action_raises_404(self):
        request = self._request("/admin/multifactor/")
        request.method = "POST"
        request.POST = {}

        view = List()
        view.request = request
        view.object = None
        view.factors = UserKey.objects.filter(user=self.user)

        with self.assertRaises(Exception):
            view.post(request, "does_not_exist", 1)

    def test_action_toggle_fallback_disable_and_enable(self):
        request = self._request("/admin/multifactor/")
        view = List()
        view.request = request
        view.object = None

        with patch("multifactor.views.mf_settings", {"FALLBACKS": {"email": (lambda u: u.email, "x")}}):
            view.action_toggle_fallback(request, "email")
            self.assertTrue(DisabledFallback.objects.filter(user=self.user, fallback="email").exists())
            view.action_toggle_fallback(request, "email")
            self.assertFalse(DisabledFallback.objects.filter(user=self.user, fallback="email").exists())

    def test_action_toggle_fallback_invalid(self):
        request = self._request("/admin/multifactor/")
        view = List()
        view.request = request
        view.object = None

        with patch("multifactor.views.messages.error") as msg_error:
            view.action_toggle_fallback(request, "bad")

        msg_error.assert_called_once()

    def test_rename_queryset_filters_user(self):
        request = self._request("/admin/multifactor/rename/1/")
        view = Rename()
        view.request = request

        qs = view.get_queryset()
        self.assertIsNotNone(qs)

    def test_authenticate_redirects_to_add_when_no_methods_available(self):
        request = self._request("/admin/multifactor/authenticate/")
        request.user = self.user

        with patch("multifactor.views.disabled_fallbacks", return_value=[]), patch(
            "multifactor.views.mf_settings", {"FALLBACKS": {}}
        ):
            response = Authenticate.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/multifactor/add/")

    def test_authenticate_redirects_to_single_method_when_no_fallbacks(self):
        request = self._request("/admin/multifactor/authenticate/")
        request.user = self.user

        UserKey.objects.create(
            user=self.user,
            key_type=KeyTypes.TOTP,
            properties={},
            enabled=True,
        )

        with patch("multifactor.views.disabled_fallbacks", return_value=[]), patch(
            "multifactor.views.mf_settings", {"FALLBACKS": {}}
        ):
            response = Authenticate.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/multifactor/totp/auth/")

    def test_authenticate_shows_other_domain_message(self):
        request = self._request("/admin/multifactor/authenticate/")
        request.user = self.user

        UserKey.objects.create(
            user=self.user,
            key_type=KeyTypes.FIDO2,
            enabled=True,
            properties={"domain": "other.example.com"},
        )

        with patch("multifactor.views.disabled_fallbacks", return_value=[]), patch(
            "multifactor.views.mf_settings", {"FALLBACKS": {"email": (lambda u: u.email, "x")}}
        ), patch("multifactor.views.messages.info") as msg_info:
            response = Authenticate.as_view()(request)

        self.assertEqual(response.status_code, 200)
        msg_info.assert_called_once()
