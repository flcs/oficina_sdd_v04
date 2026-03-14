"""Unit tests for LoginAttemptPolicy domain service.

TDD: tests are written before the implementation exists (T043).
Covers:
  - 5-failure threshold triggers lockout
  - < 5 failures do NOT trigger lockout
  - Lockout duration is 15 minutes
  - Counter should be reset on successful login
"""

from __future__ import annotations

import pytest
from datetime import timedelta


# The module under test does not exist yet; import will fail until T043.
# Running this file before T043 MUST produce ImportError / ModuleNotFoundError.
from domain.services.login_attempt_policy import LoginAttemptPolicy


class TestLockoutThreshold:
    """should_lock returns True at exactly the 5-failure threshold."""

    def test_no_lock_below_threshold(self) -> None:
        policy = LoginAttemptPolicy()
        for attempts in range(1, 5):
            assert policy.should_lock(attempts) is False, (
                f"Expected no lock for {attempts} failed attempts"
            )

    def test_lock_at_threshold(self) -> None:
        policy = LoginAttemptPolicy()
        assert policy.should_lock(5) is True

    def test_lock_above_threshold(self) -> None:
        policy = LoginAttemptPolicy()
        for attempts in range(6, 11):
            assert policy.should_lock(attempts) is True, (
                f"Expected lock for {attempts} failed attempts"
            )

    def test_no_lock_at_zero(self) -> None:
        policy = LoginAttemptPolicy()
        assert policy.should_lock(0) is False


class TestLockoutDuration:
    """lockout_duration returns 15-minute timedelta."""

    def test_duration_is_15_minutes(self) -> None:
        policy = LoginAttemptPolicy()
        expected = timedelta(minutes=15)
        assert policy.lockout_duration() == expected


class TestCounterReset:
    """should_reset_on_success indicates counter must be reset on success."""

    def test_reset_on_success(self) -> None:
        policy = LoginAttemptPolicy()
        assert policy.should_reset_on_success() is True


class TestImmutability:
    """Multiple instances are independent and stateless."""

    def test_stateless_instances(self) -> None:
        p1 = LoginAttemptPolicy()
        p2 = LoginAttemptPolicy()
        assert p1.should_lock(5) == p2.should_lock(5)
        assert p1.lockout_duration() == p2.lockout_duration()
