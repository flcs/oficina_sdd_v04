"""LoginAttemptPolicy — domain service for lockout threshold and duration.

Business rules:
  - 5 or more consecutive failed attempts trigger account lockout (FR-002).
  - Lockout duration is 15 minutes (FR-003).
  - On successful login the counter must be reset (FR-004).
  - Policy is stateless; all state lives in the Account entity.
"""

from __future__ import annotations

from datetime import timedelta

_LOCKOUT_THRESHOLD: int = 5
_LOCKOUT_DURATION_MINUTES: int = 15


class LoginAttemptPolicy:
    """Encapsulates the rules governing login attempt lockout behaviour.

    Stateless — instantiate wherever needed without shared state.
    """

    def should_lock(self, failed_attempts: int) -> bool:
        """Return True if the account should be locked based on attempt count."""
        return failed_attempts >= _LOCKOUT_THRESHOLD

    def lockout_duration(self) -> timedelta:
        """Return the duration for which an account should remain locked."""
        return timedelta(minutes=_LOCKOUT_DURATION_MINUTES)

    def should_reset_on_success(self) -> bool:
        """Return True; the failed-attempts counter is always reset on success."""
        return True
