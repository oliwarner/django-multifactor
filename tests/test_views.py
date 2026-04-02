from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse
from unittest.mock import patch

from multifactor.models import KeyTypes, UserKey
from multifactor.views import Add, Authenticate, Help, List


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

        context = view.get_context_data()

        self.assertIn("available_fallbacks", context)
        self.assertEqual(context["can_edit"], True)

    def test_help_template_name(self):
        self.assertEqual(Help.template_name, "multifactor/help.html")

    @patch("multifactor.views.active_factors", return_value=[])
    @patch("multifactor.views.has_multifactor", return_value=True)
    def test_authenticate_redirects_to_add_when_no_available_methods(self, has_multifactor, active_factors):
        request = self._request("/admin/multifactor/authenticate/")
        request.user = self.user

        UserKey.objects.create(
            user=self.user,
            key_type=KeyTypes.FIDO2,
            enabled=True,
            properties={"domain": "other.example.com"},
        )

        response = Authenticate.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/multifactor/add/")

    @patch("multifactor.views.disabled_fallbacks", return_value=[])
    @patch("multifactor.views.mf_settings", {"FALLBACKS": {}})
    def test_add_context_lists_all_methods(self, disabled_fallbacks):
        request = self._request("/admin/multifactor/add/")
        view = Add()
        view.request = request
        view.object = None

        context = view.get_context_data()

        self.assertIn("methods", context)
        self.assertTrue(context["methods"])
