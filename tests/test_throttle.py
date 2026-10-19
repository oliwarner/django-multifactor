from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from multifactor import throttle
from multifactor.models import AuthAttempt


@patch.dict(
    "multifactor.throttle.mf_settings",
    {"MAX_ATTEMPTS": 3, "ATTEMPT_PERIOD": 300, "LOCKOUT_PERIOD": 1800, "ATTEMPT_RETENTION_DAYS": 90},
)
class ThrottleTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.alice = User.objects.create_user(username="alice", password="x")
        self.bob = User.objects.create_user(username="bob", password="x")
        self.now = timezone.now()

    def log(self, user, seconds_ago, outcome="failure", factor="TOTP"):
        return AuthAttempt.objects.create(
            user=user, factor=factor, outcome=outcome, timestamp=self.now - timedelta(seconds=seconds_ago)
        )

    def test_not_locked_initially(self):
        self.assertFalse(throttle.is_locked(self.alice))
        self.assertIsNone(throttle.locked_until(self.alice))

    def test_not_locked_below_the_limit(self):
        self.log(self.alice, 10)
        self.log(self.alice, 5)

        self.assertFalse(throttle.is_locked(self.alice))

    def test_locked_when_limit_reached_within_period(self):
        for seconds_ago in (30, 20, 10):
            self.log(self.alice, seconds_ago)

        self.assertTrue(throttle.is_locked(self.alice))

    def test_lockout_runs_from_the_latest_failure(self):
        for seconds_ago in (30, 20, 10):
            self.log(self.alice, seconds_ago)

        expected = self.now - timedelta(seconds=10) + timedelta(seconds=1800)
        self.assertEqual(throttle.locked_until(self.alice), expected)

    def test_lockout_outlasts_the_attempt_period(self):
        for seconds_ago in (1000, 990, 980):  # > ATTEMPT_PERIOD ago, < LOCKOUT_PERIOD ago
            self.log(self.alice, seconds_ago)

        self.assertTrue(throttle.is_locked(self.alice))

    def test_lockout_expires(self):
        for seconds_ago in (2000, 1990, 1980):  # > LOCKOUT_PERIOD ago
            self.log(self.alice, seconds_ago)

        self.assertFalse(throttle.is_locked(self.alice))

    def test_lockout_shorter_than_period_relocks_after_one_failure(self):
        # Documented caveat: with LOCKOUT_PERIOD < ATTEMPT_PERIOD the old failures are still
        # inside the window when the lockout ends, so one new failure locks the user again.
        with patch.dict("multifactor.throttle.mf_settings", {"LOCKOUT_PERIOD": 60}):
            for seconds_ago in (200, 190, 180):
                self.log(self.alice, seconds_ago)
            self.assertFalse(throttle.is_locked(self.alice))  # lockout over (60s passed)

            self.log(self.alice, 1)

            self.assertTrue(throttle.is_locked(self.alice))

    def test_lockout_at_least_period_gives_fresh_attempts_after_expiry(self):
        for seconds_ago in (2000, 1990, 1980):  # locked, then LOCKOUT_PERIOD (1800s) passed
            self.log(self.alice, seconds_ago)

        self.log(self.alice, 1)

        self.assertFalse(throttle.is_locked(self.alice))

    def test_failures_spread_over_more_than_the_period_do_not_lock(self):
        for seconds_ago in (600, 300, 1):  # window is a sliding 300s; these span 599s
            self.log(self.alice, seconds_ago)

        self.assertFalse(throttle.is_locked(self.alice))

    def test_window_slides(self):
        for seconds_ago in (700, 20, 10, 5):  # three failures in the last 300s, one older
            self.log(self.alice, seconds_ago)

        self.assertTrue(throttle.is_locked(self.alice))

    def test_success_resets_the_run_of_failures(self):
        self.log(self.alice, 30)
        self.log(self.alice, 20)
        self.log(self.alice, 10, outcome="success")
        self.log(self.alice, 5)

        self.assertFalse(throttle.is_locked(self.alice))

    def test_blocked_attempts_are_not_counted(self):
        for seconds_ago in (30, 20):
            self.log(self.alice, seconds_ago)
        for seconds_ago in (15, 10, 5):
            self.log(self.alice, seconds_ago, outcome="blocked")

        self.assertFalse(throttle.is_locked(self.alice))

    def test_totp_and_fallback_failures_are_counted_together(self):
        self.log(self.alice, 30, factor="TOTP")
        self.log(self.alice, 20, factor="FALLBACK")
        self.log(self.alice, 10, factor="TOTP")

        self.assertTrue(throttle.is_locked(self.alice))

    def test_users_are_independent(self):
        for seconds_ago in (30, 20, 10):
            self.log(self.alice, seconds_ago)

        self.assertTrue(throttle.is_locked(self.alice))
        self.assertFalse(throttle.is_locked(self.bob))

    def test_disabled_when_max_attempts_is_zero(self):
        for seconds_ago in range(1, 20):
            self.log(self.alice, seconds_ago)

        with patch.dict("multifactor.throttle.mf_settings", {"MAX_ATTEMPTS": 0}):
            self.assertFalse(throttle.is_locked(self.alice))
            attempt = throttle.begin_attempt(self.alice, "TOTP")
            self.assertIsNotNone(attempt)
            self.assertIsNone(attempt.pk)  # nothing is written when limiting is off

    # begin_attempt / succeed

    def test_begin_attempt_records_a_failure_until_succeeded(self):
        attempt = throttle.begin_attempt(self.alice, "TOTP")

        self.assertEqual(AuthAttempt.objects.get().outcome, "failure")

        throttle.succeed(attempt)

        self.assertEqual(AuthAttempt.objects.get().outcome, "success")

    def test_begin_attempt_when_locked_logs_blocked_and_returns_none(self):
        for seconds_ago in (30, 20, 10):
            self.log(self.alice, seconds_ago)

        self.assertIsNone(throttle.begin_attempt(self.alice, "TOTP"))
        self.assertEqual(AuthAttempt.objects.filter(outcome="blocked").count(), 1)

    def test_reserving_an_attempt_counts_it_even_if_never_resolved(self):
        for _ in range(3):
            throttle.begin_attempt(self.alice, "TOTP")  # e.g. the request died mid-check

        self.assertTrue(throttle.is_locked(self.alice))

    # Retention

    def test_prune_deletes_only_old_rows(self):
        old = self.log(self.alice, 91 * 86400)
        recent = self.log(self.alice, 10)

        self.assertEqual(throttle.prune(), 1)
        self.assertFalse(AuthAttempt.objects.filter(pk=old.pk).exists())
        self.assertTrue(AuthAttempt.objects.filter(pk=recent.pk).exists())

    def test_prune_command(self):
        self.log(self.alice, 10 * 86400)
        out = StringIO()

        call_command("prune_mfa_attempts", "--days", "5", stdout=out)

        self.assertIn("Deleted 1", out.getvalue())
        self.assertEqual(AuthAttempt.objects.count(), 0)
