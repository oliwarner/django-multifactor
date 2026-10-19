from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings

from multifactor import throttle

LOCMEM_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


@override_settings(CACHES=LOCMEM_CACHE)
@patch.dict("multifactor.throttle.mf_settings", {"MAX_ATTEMPTS": 3, "ATTEMPT_PERIOD": 300})
class ThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        User = get_user_model()
        self.alice = User.objects.create_user(username="alice", password="x")
        self.bob = User.objects.create_user(username="bob", password="x")

    def test_not_locked_initially(self):
        self.assertFalse(throttle.is_locked(self.alice))

    def test_locks_when_limit_reached(self):
        self.assertFalse(throttle.record_failure(self.alice))
        self.assertFalse(throttle.record_failure(self.alice))
        self.assertTrue(throttle.record_failure(self.alice))
        self.assertTrue(throttle.is_locked(self.alice))

    def test_counters_are_per_user(self):
        for _ in range(3):
            throttle.record_failure(self.alice)

        self.assertTrue(throttle.is_locked(self.alice))
        self.assertFalse(throttle.is_locked(self.bob))

    def test_reset_clears_counter(self):
        for _ in range(3):
            throttle.record_failure(self.alice)
        throttle.reset(self.alice)

        self.assertFalse(throttle.is_locked(self.alice))

    def test_counter_expires_after_period(self):
        for _ in range(3):
            throttle.record_failure(self.alice)
        cache.delete(throttle._cache_key(self.alice))  # what expiry does

        self.assertFalse(throttle.is_locked(self.alice))
        self.assertFalse(throttle.record_failure(self.alice))

    def test_disabled_when_max_attempts_is_zero(self):
        with patch.dict("multifactor.throttle.mf_settings", {"MAX_ATTEMPTS": 0}):
            for _ in range(50):
                self.assertFalse(throttle.record_failure(self.alice))

            self.assertFalse(throttle.is_locked(self.alice))
