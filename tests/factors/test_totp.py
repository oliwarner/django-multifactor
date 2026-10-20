from unittest.mock import patch

import pyotp
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from multifactor.factors.totp import matching_step
from multifactor.models import AuthAttempt, KeyTypes, UserKey

SECRET = "JBSWY3DPEHPK3PXP"
NOW = 1_700_000_000  # arbitrary fixed instant
STEP = NOW // 30


def code_at(step, secret=SECRET):
    return pyotp.TOTP(secret).generate_otp(step)


def at_now(test):
    """Freeze the clock used by the TOTP factor."""
    return patch("multifactor.factors.totp.time.time", return_value=NOW)


@override_settings(
    ROOT_URLCONF="testsite.testsite.urls",
    MULTIFACTOR={"TOKEN_ISSUER_NAME": "Django App"},
)
class TOTPTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password123",
        )
        self.client.force_login(self.user)

    def make_key(self, **properties):
        return UserKey.objects.create(
            user=self.user,
            key_type=KeyTypes.TOTP,
            properties={"secret_key": SECRET, **properties},
        )

    # Enrolment

    @patch("multifactor.factors.totp.pyotp.random_base32", return_value=SECRET)
    def test_create_post_success(self, random_base32):
        with at_now(self):
            response = self.client.post(reverse("multifactor:totp_start"), {"answer": code_at(STEP), "key": SECRET})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("multifactor:home"))
        key = UserKey.objects.get(user=self.user, key_type=KeyTypes.TOTP)
        self.assertEqual(key.properties["secret_key"], SECRET)
        # The enrolment code is spent, so it can't be replayed to authenticate.
        self.assertEqual(key.properties["last_step"], STEP)

    def test_create_post_failure(self):
        with at_now(self):
            response = self.client.post(reverse("multifactor:totp_start"), {"answer": "000000", "key": SECRET})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(UserKey.objects.filter(user=self.user).exists())

    # Verification window

    def test_default_window_accepts_adjacent_steps(self):
        totp = pyotp.TOTP(SECRET)
        with at_now(self):
            for offset in (-1, 0, 1):
                self.assertEqual(matching_step(totp, code_at(STEP + offset)), STEP + offset)

    def test_default_window_rejects_codes_outside_one_step(self):
        totp = pyotp.TOTP(SECRET)
        with at_now(self):
            for offset in (-2, 2, -60, 60):
                self.assertIsNone(matching_step(totp, code_at(STEP + offset)))

    def test_window_is_configurable(self):
        totp = pyotp.TOTP(SECRET)
        with at_now(self), patch.dict("multifactor.factors.totp.mf_settings", {"TOTP_WINDOW": 3}):
            self.assertEqual(matching_step(totp, code_at(STEP + 3)), STEP + 3)
            self.assertIsNone(matching_step(totp, code_at(STEP + 4)))

    def test_matching_step_ignores_whitespace(self):
        with at_now(self):
            self.assertEqual(matching_step(pyotp.TOTP(SECRET), f" {code_at(STEP)} "), STEP)

    # Authentication

    def test_auth_post_success(self):
        key = self.make_key()

        with at_now(self):
            response = self.client.post(reverse("multifactor:totp_auth"), {"answer": code_at(STEP)})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.client.session["multifactor"])
        key.refresh_from_db()
        self.assertEqual(key.properties["last_step"], STEP)
        self.assertIsNotNone(key.last_used)

    def test_auth_post_failure(self):
        self.make_key()

        with at_now(self):
            response = self.client.post(reverse("multifactor:totp_auth"), {"answer": "000000"})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.client.session.get("multifactor"))

    def test_auth_post_without_answer_is_a_failure_not_an_error(self):
        self.make_key()
        response = self.client.post(reverse("multifactor:totp_auth"), {})
        self.assertEqual(response.status_code, 200)

    def test_auth_rejects_replay_of_a_used_code(self):
        self.make_key()
        with at_now(self):
            first = self.client.post(reverse("multifactor:totp_auth"), {"answer": code_at(STEP)})
            self.client.session.flush()
            self.client.force_login(self.user)
            second = self.client.post(reverse("multifactor:totp_auth"), {"answer": code_at(STEP)})

        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 200)
        self.assertFalse(self.client.session.get("multifactor"))

    def test_auth_rejects_earlier_step_after_later_one_used(self):
        self.make_key(last_step=STEP)
        with at_now(self):
            response = self.client.post(reverse("multifactor:totp_auth"), {"answer": code_at(STEP - 1)})

        self.assertEqual(response.status_code, 200)

    def test_auth_accepts_later_step_after_earlier_one_used(self):
        self.make_key(last_step=STEP - 1)
        with at_now(self):
            response = self.client.post(reverse("multifactor:totp_auth"), {"answer": code_at(STEP)})

        self.assertEqual(response.status_code, 302)

    def test_disabled_keys_are_ignored(self):
        key = self.make_key()
        key.enabled = False
        key.save()
        with at_now(self):
            response = self.client.post(reverse("multifactor:totp_auth"), {"answer": code_at(STEP)})

        self.assertEqual(response.status_code, 200)

    # Attempt logging and lockout

    def attempts(self, outcome):
        return AuthAttempt.objects.filter(user=self.user, factor="TOTP", outcome=outcome).count()

    def test_attempts_are_logged(self):
        self.make_key()
        url = reverse("multifactor:totp_auth")

        with at_now(self):
            self.client.post(url, {"answer": "000000"})
            self.client.post(url, {"answer": code_at(STEP)})

        self.assertEqual(self.attempts("failure"), 1)
        self.assertEqual(self.attempts("success"), 1)

    @patch.dict("multifactor.throttle.mf_settings", {"MAX_ATTEMPTS": 3})
    def test_lockout_after_max_failures_logs_user_out(self):
        self.make_key()
        url = reverse("multifactor:totp_auth")

        with at_now(self), self.assertLogs("multifactor.throttle", level="WARNING"):
            self.assertEqual(self.client.post(url, {"answer": "000000"}).status_code, 200)
            self.assertEqual(self.client.post(url, {"answer": "000000"}).status_code, 200)
            locked = self.client.post(url, {"answer": "000000"})

        self.assertEqual(locked.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

    @patch.dict("multifactor.throttle.mf_settings", {"MAX_ATTEMPTS": 2})
    def test_locked_user_cannot_pass_with_a_valid_code(self):
        self.make_key()
        url = reverse("multifactor:totp_auth")

        with at_now(self), self.assertLogs("multifactor.throttle", level="WARNING"):
            self.client.post(url, {"answer": "000000"})
            self.client.post(url, {"answer": "000000"})  # reaches the limit

            self.client.force_login(self.user)
            response = self.client.post(url, {"answer": code_at(STEP)})

        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertFalse(self.client.session.get("multifactor"))
        self.assertEqual(self.attempts("blocked"), 1)
        self.assertEqual(self.attempts("success"), 0)

    @patch.dict("multifactor.throttle.mf_settings", {"MAX_ATTEMPTS": 3})
    def test_blocked_attempts_do_not_extend_the_lockout(self):
        from datetime import timedelta

        from django.utils import timezone

        self.make_key()
        now = timezone.now()
        for seconds_ago in (3000, 2900, 2800):  # lockout (30 min) ended well before now
            AuthAttempt.objects.create(
                user=self.user, factor="TOTP", outcome="failure", timestamp=now - timedelta(seconds=seconds_ago)
            )
        AuthAttempt.objects.create(user=self.user, factor="TOTP", outcome="blocked")

        with at_now(self):
            response = self.client.post(reverse("multifactor:totp_auth"), {"answer": code_at(STEP)})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.client.session["multifactor"])

    @patch.dict("multifactor.throttle.mf_settings", {"MAX_ATTEMPTS": 3})
    def test_success_resets_the_failure_count(self):
        self.make_key()
        url = reverse("multifactor:totp_auth")

        with at_now(self):
            self.client.post(url, {"answer": "000000"})
            self.client.post(url, {"answer": "000000"})
            self.client.post(url, {"answer": code_at(STEP)})  # success
            self.client.force_login(self.user)
            response = self.client.post(url, {"answer": "000000"})

        self.assertEqual(response.status_code, 200)  # not locked out

    @patch.dict("multifactor.throttle.mf_settings", {"MAX_ATTEMPTS": 0})
    def test_throttle_can_be_disabled(self):
        self.make_key()
        url = reverse("multifactor:totp_auth")

        with at_now(self):
            for _ in range(20):
                self.assertEqual(self.client.post(url, {"answer": "000000"}).status_code, 200)

        self.assertEqual(AuthAttempt.objects.count(), 0)
