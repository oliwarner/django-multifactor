from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.views import View
from unittest.mock import patch

from multifactor.mixins import MultiFactorMixin, PreferMultiAuthMixin, RequireMultiAuthMixin


class MultiFactorMixinTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password123",
        )

    @patch("multifactor.mixins.active_factors", return_value=[])
    @patch("multifactor.mixins.is_bypassed", return_value=False)
    def test_setup_populates_state_for_authenticated_user(self, is_bypassed, active_factors):
        request = self.factory.get("/")
        request.user = self.user

        class DummyView(MultiFactorMixin, View):
            def get(self, request, *args, **kwargs):
                return HttpResponse("ok")

        view = DummyView()
        view.setup(request)

        self.assertEqual(view.active_factors, [])
        self.assertEqual(view.factors.count(), 0)
        self.assertFalse(view.has_multifactor)
        self.assertFalse(view.bypass)

    @patch("multifactor.mixins.active_factors")
    @patch("multifactor.mixins.is_bypassed")
    def test_setup_skips_unauthenticated_user(self, is_bypassed, active_factors):
        request = self.factory.get("/")
        request.user = type("Anon", (), {"is_authenticated": False})()

        class DummyView(MultiFactorMixin, View):
            def get(self, request, *args, **kwargs):
                return HttpResponse("ok")

        view = DummyView()
        view.setup(request)

        self.assertFalse(hasattr(view, "active_factors"))
        self.assertFalse(hasattr(view, "has_multifactor"))

    @patch("multifactor.mixins.active_factors", return_value=[])
    @patch("multifactor.mixins.is_bypassed", return_value=False)
    def test_require_multi_auth_redirects_to_add_when_no_keys(self, is_bypassed, active_factors):
        request = self.factory.get("/protected/")
        request.user = self.user
        request.session = {}

        class DummyView(RequireMultiAuthMixin, View):
            def get(self, request, *args, **kwargs):
                return HttpResponse("ok")

        response = DummyView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/multifactor/add/")

    @patch("multifactor.mixins.active_factors", return_value=[])
    @patch("multifactor.mixins.is_bypassed", return_value=False)
    def test_prefer_multi_auth_redirects_to_authenticate_when_has_keys(self, is_bypassed, active_factors):
        request = self.factory.get("/protected/")
        request.user = self.user
        request.session = {}

        class DummyView(PreferMultiAuthMixin, View):
            def get(self, request, *args, **kwargs):
                return HttpResponse("ok")

        with patch("multifactor.mixins.UserKey.objects.filter") as filter_mock:
            filter_mock.return_value.filter.return_value.exists.return_value = True
            response = DummyView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/multifactor/authenticate/")
