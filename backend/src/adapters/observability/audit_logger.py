"""Structured audit logger adapter (full implementation — T047).

Logs login attempt events as structured JSON to the 'audit' logger.
Includes derived events for lock_start and lock_release outcomes.
"""

from __future__ import annotations

import json
import logging

from application.ports.auth_ports import AuditLogPort
from domain.entities.account import AccountOutcome, LoginAttempt

logger = logging.getLogger("audit")

# Outcomes that indicate a fresh lockout has just been applied
_LOCK_TRIGGER_OUTCOMES = frozenset({AccountOutcome.LOCKED})


class StructuredAuditLogger(AuditLogPort):
    """Logs login attempt events as structured JSON to the audit logger."""

    def log_login_attempt(self, attempt: LoginAttempt) -> None:
        entry = {
            "event": "login_attempt",
            "attempt_id": str(attempt.attempt_id),
            "email_submitted": attempt.email_submitted,
            "account_id": str(attempt.account_id) if attempt.account_id else None,
            "outcome": attempt.outcome.value,
            "occurred_at": attempt.occurred_at.isoformat(),
            "source_ip": attempt.source_ip,
            "user_agent": attempt.user_agent,
        }
        logger.info(json.dumps(entry))

        # Emit a supplementary lock_start event to make lockouts visible in audits
        if attempt.outcome == AccountOutcome.LOCKED:
            lock_entry = {
                "event": "lock_start",
                "attempt_id": str(attempt.attempt_id),
                "account_id": str(attempt.account_id) if attempt.account_id else None,
                "occurred_at": attempt.occurred_at.isoformat(),
            }
            logger.warning(json.dumps(lock_entry))

        # Emit a lock_release event when credentials succeed (counter was reset)
        if attempt.outcome == AccountOutcome.SUCCESS:
            release_entry = {
                "event": "lock_release_candidate",
                "attempt_id": str(attempt.attempt_id),
                "account_id": str(attempt.account_id) if attempt.account_id else None,
                "occurred_at": attempt.occurred_at.isoformat(),
            }
            logger.info(json.dumps(release_entry))
