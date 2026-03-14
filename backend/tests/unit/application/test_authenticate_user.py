"""Unit tests for the AuthenticateUser use case.

TDD: tests are written before the implementation exists.
All external dependencies are replaced with in-memory fakes.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import pytest

from domain.entities.account import Account, AccountRole, AccountOutcome, Email, AuthSession
from application.ports.auth_ports import (
    UserAccountRepository,
    PasswordHasher,
    TokenService,
    Clock,
    AuditLogPort,
    UnitOfWork,
)
from domain.entities.account import LoginAttempt


# ── Fakes ─────────────────────────────────────────────────────────────────────

class FakeClock(Clock):
    def __init__(self, fixed: datetime) -> None:
        self._now = fixed

    def utc_now(self) -> datetime:
        return self._now


class FakePasswordHasher(PasswordHasher):
    def hash(self, plain: str) -> str:
        return f"hashed:{plain}"

    def verify(self, plain: str, hashed: str) -> bool:
        return hashed == f"hashed:{plain}"


class FakeTokenService(TokenService):
    def create_access_token(
        self,
        account_id: uuid.UUID,
        role: str,
        must_change_password: bool,
        token_version: int,
    ) -> AuthSession:
        now = datetime(2024, 1, 1, tzinfo=timezone.utc)
        return AuthSession(
            account_id=account_id,
            access_token=f"token-{account_id}",
            issued_at=now,
            expires_at=now + timedelta(minutes=30),
            must_change_password=must_change_password,
        )

    def decode_access_token(self, token: str) -> dict[str, object]:
        return {}


class FakeAuditLog(AuditLogPort):
    def __init__(self) -> None:
        self.entries: list[LoginAttempt] = []

    def log_login_attempt(self, attempt: LoginAttempt) -> None:
        self.entries.append(attempt)


class FakeUnitOfWork(UnitOfWork):
    committed = False

    def __enter__(self) -> "FakeUnitOfWork":
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass


class InMemoryAccountRepository(UserAccountRepository):
    def __init__(self, accounts: list[Account] | None = None) -> None:
        self._accounts: dict[str, Account] = {}
        for acc in accounts or []:
            self._accounts[acc.email.value] = acc

    def find_by_email(self, email: str) -> Optional[Account]:
        return self._accounts.get(email.lower().strip())

    def find_by_id(self, account_id: uuid.UUID) -> Optional[Account]:
        return next(
            (a for a in self._accounts.values() if a.account_id == account_id), None
        )

    def save(self, account: Account) -> None:
        self._accounts[account.email.value] = account

    def increment_failed_attempts(
        self, account_id: uuid.UUID, locked_until: Optional[datetime]
    ) -> None:
        for email, acc in self._accounts.items():
            if acc.account_id == account_id:
                self._accounts[email] = Account(
                    account_id=acc.account_id,
                    email=acc.email,
                    password_hash=acc.password_hash,
                    role=acc.role,
                    active=acc.active,
                    must_change_password=acc.must_change_password,
                    failed_login_attempts=acc.failed_login_attempts + 1,
                    locked_until=locked_until,
                    token_version=acc.token_version,
                    created_at=acc.created_at,
                    updated_at=acc.updated_at,
                )

    def reset_failed_attempts(self, account_id: uuid.UUID) -> None:
        for email, acc in self._accounts.items():
            if acc.account_id == account_id:
                self._accounts[email] = Account(
                    account_id=acc.account_id,
                    email=acc.email,
                    password_hash=acc.password_hash,
                    role=acc.role,
                    active=acc.active,
                    must_change_password=acc.must_change_password,
                    failed_login_attempts=0,
                    locked_until=None,
                    token_version=acc.token_version,
                    created_at=acc.created_at,
                    updated_at=acc.updated_at,
                )

    def bootstrap_admin(self, email: str, password_hash: str, role: str) -> str:
        return "preserved"

    def record_login_attempt(self, attempt: LoginAttempt) -> None:
        pass


def _make_account(
    email: str = "user@empresa.com",
    active: bool = True,
    must_change_password: bool = False,
    failed_login_attempts: int = 0,
    locked_until: Optional[datetime] = None,
) -> Account:
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return Account(
        account_id=uuid.uuid4(),
        email=Email(email),
        password_hash="hashed:correct",
        role=AccountRole.USER,
        active=active,
        must_change_password=must_change_password,
        failed_login_attempts=failed_login_attempts,
        locked_until=locked_until,
        token_version=0,
        created_at=now,
        updated_at=now,
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestAuthenticateUserSuccess:
    def test_returns_auth_session_on_valid_credentials(self) -> None:
        """Given an active account with valid credentials, a session is returned."""
        from application.use_cases.authenticate_user import AuthenticateUser

        account = _make_account()
        repo = InMemoryAccountRepository([account])
        use_case = AuthenticateUser(
            repo=repo,
            hasher=FakePasswordHasher(),
            token_svc=FakeTokenService(),
            clock=FakeClock(datetime(2024, 1, 1, tzinfo=timezone.utc)),
            audit_log=FakeAuditLog(),
        )

        session = use_case.execute(email="user@empresa.com", password="correct")

        assert session.account_id == account.account_id
        assert session.access_token.startswith("token-")
        assert session.must_change_password is False

    def test_resets_failed_attempts_on_success(self) -> None:
        """Successful login zeroes the failed_login_attempts counter."""
        from application.use_cases.authenticate_user import AuthenticateUser

        account = _make_account(failed_login_attempts=3)
        repo = InMemoryAccountRepository([account])
        use_case = AuthenticateUser(
            repo=repo,
            hasher=FakePasswordHasher(),
            token_svc=FakeTokenService(),
            clock=FakeClock(datetime(2024, 1, 1, tzinfo=timezone.utc)),
            audit_log=FakeAuditLog(),
        )

        use_case.execute(email="user@empresa.com", password="correct")

        updated = repo.find_by_email("user@empresa.com")
        assert updated is not None
        assert updated.failed_login_attempts == 0


@pytest.mark.unit
class TestAuthenticateUserInvalidCredentials:
    def test_raises_on_wrong_password(self) -> None:
        """Wrong password raises AuthenticationError."""
        from application.use_cases.authenticate_user import AuthenticateUser
        from adapters.http.error_handlers import AuthenticationError

        account = _make_account()
        repo = InMemoryAccountRepository([account])
        use_case = AuthenticateUser(
            repo=repo,
            hasher=FakePasswordHasher(),
            token_svc=FakeTokenService(),
            clock=FakeClock(datetime(2024, 1, 1, tzinfo=timezone.utc)),
            audit_log=FakeAuditLog(),
        )

        with pytest.raises(AuthenticationError):
            use_case.execute(email="user@empresa.com", password="wrong")

    def test_raises_on_unknown_email(self) -> None:
        """Unknown email raises AuthenticationError (no enumeration)."""
        from application.use_cases.authenticate_user import AuthenticateUser
        from adapters.http.error_handlers import AuthenticationError

        repo = InMemoryAccountRepository([])
        use_case = AuthenticateUser(
            repo=repo,
            hasher=FakePasswordHasher(),
            token_svc=FakeTokenService(),
            clock=FakeClock(datetime(2024, 1, 1, tzinfo=timezone.utc)),
            audit_log=FakeAuditLog(),
        )

        with pytest.raises(AuthenticationError):
            use_case.execute(email="nobody@empresa.com", password="any")

    def test_increments_failed_attempts_on_wrong_password(self) -> None:
        """Failed login increments the failed_login_attempts counter."""
        from application.use_cases.authenticate_user import AuthenticateUser
        from adapters.http.error_handlers import AuthenticationError

        account = _make_account()
        repo = InMemoryAccountRepository([account])
        use_case = AuthenticateUser(
            repo=repo,
            hasher=FakePasswordHasher(),
            token_svc=FakeTokenService(),
            clock=FakeClock(datetime(2024, 1, 1, tzinfo=timezone.utc)),
            audit_log=FakeAuditLog(),
        )

        with pytest.raises(AuthenticationError):
            use_case.execute(email="user@empresa.com", password="wrong")

        updated = repo.find_by_email("user@empresa.com")
        assert updated is not None
        assert updated.failed_login_attempts == 1


@pytest.mark.unit
class TestAuthenticateUserInactiveAccount:
    def test_raises_on_inactive_account(self) -> None:
        """Inactive account raises AuthenticationError (neutral message)."""
        from application.use_cases.authenticate_user import AuthenticateUser
        from adapters.http.error_handlers import AuthenticationError

        account = _make_account(active=False)
        repo = InMemoryAccountRepository([account])
        use_case = AuthenticateUser(
            repo=repo,
            hasher=FakePasswordHasher(),
            token_svc=FakeTokenService(),
            clock=FakeClock(datetime(2024, 1, 1, tzinfo=timezone.utc)),
            audit_log=FakeAuditLog(),
        )

        with pytest.raises(AuthenticationError):
            use_case.execute(email="user@empresa.com", password="correct")
