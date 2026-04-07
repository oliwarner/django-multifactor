import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import reverse

from multifactor.models import KeyTypes, UserKey


@override_settings(
    ROOT_URLCONF="testsite.testsite.urls",
    MULTIFACTOR={
        "FIDO_SERVER_ID": "example.com",
        "FIDO_SERVER_NAME": "Django App",
    },
)
class Fido2Tests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password123",
        )
        self.client.force_login(self.user)

    @patch("multifactor.factors.fido2.Fido2Server")
    def test_server_property_uses_settings(self, server_cls):
        import multifactor.factors.fido2 as fido2_module

        with patch.dict(
            fido2_module.mf_settings,
            {"FIDO_SERVER_ID": "example.com", "FIDO_SERVER_NAME": "Django App"},
            clear=False,
        ):
            view = fido2_module.FidoClass()
            _ = view.server

        server_cls.assert_called_once()
        kwargs = server_cls.call_args.kwargs
        self.assertEqual(kwargs["rp"]["id"], "example.com")
        self.assertEqual(kwargs["rp"]["name"], "Django App")

    def test_get_user_credentials_returns_empty_for_anonymous(self):
        from multifactor.factors.fido2 import FidoClass

        view = FidoClass()
        view.request = SimpleNamespace(user=SimpleNamespace(is_authenticated=False))

        self.assertEqual(view.get_user_credentials(), [])

    @patch("multifactor.factors.fido2.websafe_decode", return_value=b"decoded")
    @patch("multifactor.factors.fido2.AttestedCredentialData")
    def test_get_user_credentials_returns_enabled_fido2_keys(self, attested_cls, websafe_decode):
        from multifactor.factors.fido2 import FidoClass

        UserKey.objects.create(
            user=self.user,
            key_type=KeyTypes.FIDO2,
            enabled=True,
            properties={"device": "abc", "domain": "example.com"},
        )

        view = FidoClass()
        view.request = SimpleNamespace(
            user=self.user,
            get_host=lambda: "example.com",
        )

        result = view.get_user_credentials()

        self.assertEqual(len(result), 1)
        websafe_decode.assert_called_once_with("abc")
        attested_cls.assert_called_once()

    @patch("multifactor.factors.fido2.Fido2Server")
    def test_register_get_returns_json(self, server_cls):
        server = MagicMock()
        server.register_begin.return_value = ({"challenge": "abc"}, {"state": "xyz"})
        server_cls.return_value = server

        response = self.client.get(reverse("multifactor:fido2_register"))

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(payload["challenge"], "abc")
        self.assertIn("fido_state", self.client.session)

    @patch("multifactor.factors.fido2.websafe_encode", return_value="encoded-device")
    @patch("multifactor.factors.fido2.Fido2Server")
    def test_register_post_success(self, server_cls, websafe_encode):
        server = MagicMock()
        auth_data = MagicMock()
        auth_data.credential_data = b"cred-data"
        server.register_complete.return_value = auth_data
        server.rp = SimpleNamespace(id="example.com")
        server_cls.return_value = server

        session = self.client.session
        session["fido_state"] = {"state": "xyz"}
        session.save()

        request_body = {
            "type": "public-key",
            "response": {"clientDataJSON": "x", "attestationObject": "y"},
        }

        with patch("multifactor.factors.fido2.write_session") as write_session, patch(
            "multifactor.factors.fido2.messages.success"
        ) as msg_success:
            response = self.client.post(
                reverse("multifactor:fido2_register"),
                data=json.dumps(request_body),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "OK")
        self.assertTrue(UserKey.objects.filter(user=self.user, key_type=KeyTypes.FIDO2).exists())
        write_session.assert_called_once()
        msg_success.assert_called_once()
        websafe_encode.assert_called_once_with(b"cred-data")

    @patch("multifactor.factors.fido2.Fido2Server")
    def test_register_post_failure(self, server_cls):
        server = MagicMock()
        server.register_complete.side_effect = Exception("boom")
        server_cls.return_value = server

        session = self.client.session
        session["fido_state"] = {"state": "xyz"}
        session.save()

        response = self.client.post(
            reverse("multifactor:fido2_register"),
            data=json.dumps({"type": "public-key"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ERR")

    @patch("multifactor.factors.fido2.Fido2Server")
    def test_authenticate_get_returns_json(self, server_cls):
        server = MagicMock()
        server.authenticate_begin.return_value = ({"challenge": "abc"}, {"state": "xyz"})
        server_cls.return_value = server

        UserKey.objects.create(
            user=self.user,
            key_type=KeyTypes.FIDO2,
            enabled=True,
            properties={"device": "abc", "domain": "example.com"},
        )

        response = self.client.get(reverse("multifactor:fido2_authenticate"))

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(payload["challenge"], "abc")
        self.assertIn("fido_state", self.client.session)

    @patch("multifactor.factors.fido2.websafe_decode", return_value=b"decoded")
    @patch("multifactor.factors.fido2.AttestedCredentialData")
    @patch("multifactor.factors.fido2.Fido2Server")
    def test_authenticate_post_success(self, server_cls, attested_cls, websafe_decode):
        server = MagicMock()
        cred = MagicMock()
        cred.credential_id = b"cred-id"
        server.authenticate_complete.return_value = cred
        server_cls.return_value = server

        attested = MagicMock()
        attested.credential_id = b"cred-id"
        attested_cls.return_value = attested

        UserKey.objects.create(
            user=self.user,
            key_type=KeyTypes.FIDO2,
            enabled=True,
            properties={"device": "abc", "domain": "example.com"},
        )

        session = self.client.session
        session["fido_state"] = {"state": "xyz"}
        session.save()

        with patch("multifactor.factors.fido2.write_session") as write_session, patch(
            "multifactor.factors.fido2.login"
        ) as login:
            login_response = HttpResponse()
            login_response["Location"] = "/admin/multifactor/"
            login.return_value = login_response

            response = self.client.post(
                reverse("multifactor:fido2_authenticate"),
                data=json.dumps({"type": "public-key"}),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "OK")
        self.assertIn("redirect", response.json())
        write_session.assert_called_once()
        login.assert_called_once()

    @patch("multifactor.factors.fido2.AttestedCredentialData")
    @patch("multifactor.factors.fido2.websafe_decode", return_value=b"decoded")
    @patch("multifactor.factors.fido2.Fido2Server")
    def test_authenticate_post_failure(self, server_cls, websafe_decode, attested_cls):
        server = MagicMock()
        cred = MagicMock()
        cred.credential_id = b"different-cred-id"
        server.authenticate_complete.return_value = cred
        server_cls.return_value = server

        attested = MagicMock()
        attested.credential_id = b"other-cred-id"
        attested_cls.return_value = attested

        session = self.client.session
        session["fido_state"] = {"state": "xyz"}
        session.save()

        UserKey.objects.create(
            user=self.user,
            key_type=KeyTypes.FIDO2,
            enabled=True,
            properties={"device": "abc", "domain": "example.com"},
        )

        response = self.client.post(
            reverse("multifactor:fido2_authenticate"),
            data=json.dumps({"type": "public-key"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "err")
