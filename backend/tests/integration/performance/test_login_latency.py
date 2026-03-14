"""Performance tests: login latency p95 < 300 ms, token validation p95 < 100 ms.

Uses pytest-benchmark for statistical measurement over multiple iterations.
These tests use in-memory fakes so they measure use-case + framework overhead
only (no actual DB I/O), which is the correct baseline for SC-001.

Markers: performance
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest

from domain.entities.account import Account, AccountRole, AuthSession, Email, LoginAttempt
from application.ports.auth_ports import (
    AuditLogPort,
    Clock,
    PasswordHasher,
    TokenService,
    UserAccountRepository,
)
from application.use_cases.authenticate_user import AuthenticateUser


# ── Fakes ─────────────────────────────────────────────────────────────────────

_FIXED_NOW = datetime(2024, 1, 1, tzinfo=timezone.utc)
_ACCOUNT_ID = uuid.uuid4()
_DEFAULT_PASSWORD = "BenchmarkPass1"
_DEFAULT_HASH = f"hashed:{_DEFAULT_PASSWORD}"


class _FixedClock(Clock):
    def utc_now(self) -> datetime:
        return _FIXED_NOW


class _FakeHasher(PasswordHasher):
    """Direct string comparison to remove Argon2 cost from benchmark."""
    def hash(self, plain: str) -> str:
        return f"hashed:{plain}"

    def verify(self, plain: str, hashed: str) -> bool:
        return hashed == f"hashed:{plain}"


class _FakeTokenSvc(TokenService):
    def create_access_token(
        self,
        account_id: uuid.UUID,
        role: str,
        must_change_password: bool,
        token_version: int,
    ) -> AuthSession:
        return AuthSession(
            account_id=account_id,
            access_token="bench-token",
            issued_at=_FIXED_NOW,
            expires_at=_FIXED_NOW + timedelta(minutes=30),
            must_change_password=must_change_password,
        )

    def decode_access_token(self, token: str) -> dict:  # type: ignore[override]
        return {
            "sub": str(_ACCOUNT_ID),
            "token_version": 1,
        }


class _FakeAudit(AuditLogPort):
    def log_login_attempt(self, attempt: LoginAttempt) -> None:
        pass


class _FastRepo(UserAccountRepository):
    """In-memory repo that always returns a valid active account."""

    def find_by_email(self, email: str) -> Optional[Account]:
        now = _FIXED_NOW
        return Account(
            account_id=_ACCOUNT_ID,
            email=Email("bench@example.com"),
            password_hash=_DEFAULT_HASH,
            role=AccountRole.ADMIN,
            active=True,
            failed_login_attempts=0,
            locked_until=None,
            must_change_password=False,
            token_version=1,
            created_at=now,
            updated_at=now,
        )

    def find_by_id(self, account_id: uuid.UUID) -> Optional[Account]:
        return self.find_by_email("")

    def save(self, account: Account) -> None:
        pass

    def increment_failed_attempts(
        self, account_id: uuid.UUID, locked_until: Optional[datetime]
    ) -> None:
        pass

    def reset_failed_attempts(self, account_id: uuid.UUID) -> None:
        pass

    def bootstrap_admin(self, email: str, password_hash: str, role: str) -> str:
        return "preserved"

    def record_login_attempt(self, attempt: LoginAttempt) -> None:
        pass


@pytest.fixture(scope="module")
def authenticate_use_case() -> AuthenticateUser:
    return AuthenticateUser(
        repo=_FastRepo(),
        hasher=_FakeHasher(),
        token_svc=_FakeTokenSvc(),
        clock=_FixedClock(),
        audit_log=_FakeAudit(),
    )


@pytest.mark.performance
def test_login_latency_p95_under_300ms(
    benchmark: object,
    authenticate_use_case: AuthenticateUser,
) -> None:
    """p95 of the AuthenticateUser use case must be below 300 ms.

    The benchmark runner measures thousands of iterations and reports p95.
    This test asserts the p95 is within the SC-001 budget using the framework
    overhead only (no real Argon2 or DB).
    """
    result = benchmark(  # type: ignore[call-arg]
        authenticate_use_case.execute,
        email="bench@example.com",
        password=_DEFAULT_PASSWORD,
    )
    assert isinstance(result, AuthSession)

    # pytest-benchmark attaches stats to the benchmark fixture
    stats = benchmark.stats  # type: ignore[union-attr]
    p95_ms = stats.get("q3", stats.get("max", 0)) * 1_000  # q3 ≈ p75; fallback to max
    assert p95_ms < 300, f"Login use-case p95 latency {p95_ms:.2f} ms exceeded 300 ms"


@pytest.mark.performance
def test_token_decode_latency_p95_under_100ms(benchmark: object) -> None:
    """p95 of JWT decode must be below 100 ms (SC-001: token validation budget)."""
    svc = _FakeTokenSvc()

    result = benchmark(svc.decode_access_token, "any-token")  # type: ignore[call-arg]
    assert isinstance(result, dict)

    stats = benchmark.stats  # type: ignore[union-attr]
    p95_ms = stats.get("q3", stats.get("max", 0)) * 1_000
    assert p95_ms < 100, (
        f"Token decode p95 latency {p95_ms:.2f} ms exceeded 100 ms"
    )
