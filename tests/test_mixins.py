from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.views import View

from multifactor.mixins import MultiFactorMixin, RequireMultiAuthMixin, PreferMultiAuthMixin
from multifactor.models import KeyTypes, UserKey


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


class RequireMultiAuthMixinTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password123",
        )

    def test_redirects_to_add_when_user_has_no_factors(self):
        request = self.factory.get("/protected/")
        request.user = self.user
        request.session = {}

        class DummyView(RequireMultiAuthMixin, View):
            def get(self, request, *args, **kwargs):
                return HttpResponse("ok")

        view = DummyView()
        with patch("multifactor.mixins.active_factors", return_value=[]), \
             patch("multifactor.mixins.is_bypassed", return_value=False), \
             patch.object(UserKey.objects, "filter") as filter_mock:
            filter_mock.return_value = UserKey.objects.none()
            view.setup(request)
            response = view.dispatch(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/multifactor/add/")
        self.assertEqual(request.session["multifactor-next"], "/protected/")

    def test_redirects_to_authenticate_when_user_has_factors(self):
        request = self.factory.get("/protected/")
        request.user = self.user
        request.session = {}

        class DummyView(RequireMultiAuthMixin, View):
            def get(self, request, *args, **kwargs):
                return HttpResponse("ok")

        view = DummyView()
        with patch("multifactor.mixins.active_factors", return_value=[]), \
                patch("multifactor.mixins.is_bypassed", return_value=False), \
                patch.object(UserKey.objects, "filter") as filter_mock:
            qs = UserKey.objects.none()
            qs.exists = lambda: True
            filter_mock.return_value = qs
            view.setup(request)
            view.active_factors = []
            view.has_multifactor = True
            response = view.dispatch(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/multifactor/authenticate/")


class PreferMultiAuthMixinTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password123",
        )

    def test_redirects_to_authenticate_when_user_has_active_factors(self):
        request = self.factory.get("/protected/")
        request.user = self.user
        request.session = {}

        class DummyView(PreferMultiAuthMixin, View):
            def get(self, request, *args, **kwargs):
                return HttpResponse("ok")

        view = DummyView()
        fake_factor = UserKey(user=self.user, key_type=KeyTypes.TOTP, properties={})

        with patch("multifactor.mixins.active_factors", return_value=[("factor", "TOTP")]), \
                patch("multifactor.mixins.is_bypassed", return_value=False), \
                patch.object(UserKey.objects, "filter") as filter_mock:
            qs = UserKey.objects.none()
            qs.exists = lambda: True
            filter_mock.return_value = qs
            view.setup(request)
            view.active_factors = []
            view.has_multifactor = True
            response = view.dispatch(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/multifactor/authenticate/")
