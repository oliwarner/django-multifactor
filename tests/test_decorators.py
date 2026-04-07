from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from multifactor.decorators import multifactor_protected


class DecoratorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password123",
        )

    def _request(self, path="/protected/"):
        request = self.factory.get(path)
        request.user = self.user
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    def test_allows_anonymous_user(self):
        request = self.factory.get("/public/")
        request.user = type("Anon", (), {"is_authenticated": False})()

        @multifactor_protected()
        def view(request):
            return HttpResponse("ok")

        response = view(request)
        self.assertEqual(response.status_code, 200)

    def test_bypass_allows_access(self):
        request = self._request()

        @multifactor_protected()
        def view(request):
            return HttpResponse("ok")

        with patch("multifactor.decorators.is_bypassed", return_value=True):
            response = view(request)

        self.assertEqual(response.status_code, 200)

    def test_user_filter_mismatch_allows_access(self):
        request = self._request()

        @multifactor_protected(user_filter={"username": "bob"})
        def view(request):
            return HttpResponse("ok")

        with patch("multifactor.decorators.get_user_model") as gum:
            gum.return_value.objects.filter.return_value.exists.return_value = False
            response = view(request)

        self.assertEqual(response.status_code, 200)

    def test_redirects_when_required_factors_not_met(self):
        request = self._request()

        @multifactor_protected(factors=2)
        def view(request):
            return HttpResponse("ok")

        with patch("multifactor.decorators.active_factors", return_value=[("k1", "TOTP")]), patch(
            "multifactor.decorators.has_multifactor", return_value=True
        ):
            response = view(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(request.session["multifactor-next"], "/protected/")
        self.assertEqual(response["Location"], "/admin/multifactor/authenticate/")

    def test_redirects_to_authenticate_when_user_has_multifactor_but_no_active(self):
        request = self._request()

        @multifactor_protected()
        def view(request):
            return HttpResponse("ok")

        with patch("multifactor.decorators.active_factors", return_value=[]), patch(
            "multifactor.decorators.has_multifactor", return_value=True
        ):
            response = view(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/multifactor/authenticate/")

    def test_advertise_adds_message(self):
        request = self._request()

        @multifactor_protected(advertise=True)
        def view(request):
            return HttpResponse("ok")

        with patch("multifactor.decorators.active_factors", return_value=[]), patch(
            "multifactor.decorators.has_multifactor", return_value=False
        ), patch("multifactor.decorators.is_bypassed", return_value=False), patch(
            "multifactor.decorators.messages.info"
        ) as msg_info:
            response = view(request)

        self.assertEqual(response.status_code, 200)
        msg_info.assert_called_once()

    def test_max_age_forces_reauth(self):
        request = self._request()

        @multifactor_protected(max_age=60)
        def view(request):
            return HttpResponse("ok")

        with patch("multifactor.decorators.active_factors", return_value=[("key", "TOTP", "name", 0)]), patch(
            "multifactor.decorators.has_multifactor", return_value=True
        ), patch("multifactor.decorators.timezone.now") as now:
            now.return_value.timestamp.return_value = 999999
            response = view(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/multifactor/authenticate/")

    def test_allows_access_when_required_factors_are_met(self):
        request = self._request()

        @multifactor_protected(factors=1)
        def view(request):
            return HttpResponse("ok")

        with patch("multifactor.decorators.active_factors", return_value=[("k1", "TOTP")]), patch(
            "multifactor.decorators.has_multifactor", return_value=True
        ):
            response = view(request)

        self.assertEqual(response.status_code, 200)

    def test_function_based_factors_are_evaluated(self):
        request = self._request()

        @multifactor_protected(factors=lambda req: 1)
        def view(request):
            return HttpResponse("ok")

        with patch("multifactor.decorators.active_factors", return_value=[("k1", "TOTP")]), patch(
            "multifactor.decorators.has_multifactor", return_value=True
        ):
            response = view(request)

        self.assertEqual(response.status_code, 200)
