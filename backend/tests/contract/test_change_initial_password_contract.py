"""Contract tests for POST /auth/change-initial-password.

Validates HTTP-level contract:
  200 — password changed successfully
  401 — missing/invalid token OR current password incorrect
  409 — account does not require initial password change

TDD: written before T034 (change_password_controller implementation).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI


def _make_token(must_change_password: bool = True) -> str:
    """Build a test bearer token via a fake TokenService."""
    import jwt as pyjwt

    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    payload = {
        "sub": "00000000-0000-0000-0000-000000000001",
        "iss": "test-issuer",
        "aud": "test-audience",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=30)).timestamp()),
        "jti": str(uuid.uuid4()),
        "role": "admin",
        "must_change_password": must_change_password,
        "token_version": 0,
    }
    return pyjwt.encode(payload, "test-secret", algorithm="HS256")


def _make_app(must_change_password: bool = True) -> FastAPI:
    from domain.entities.account import Account, AccountRole, AuthSession, Email, LoginAttempt
    from application.ports.auth_ports import (
        UserAccountRepository,
        PasswordHasher,
        TokenService,
        Clock,
        AuditLogPort,
    )
    from adapters.http.error_handlers import register_error_handlers
    from adapters.security.jwt_token_service import JwtTokenService
    from infrastructure.clock import SystemClock

    class _FakeHasher(PasswordHasher):
        def hash(self, plain: str) -> str:
            return f"hashed:{plain}"

        def verify(self, plain: str, hashed: str) -> bool:
            return hashed == f"hashed:{plain}"

    class _FakeAudit(AuditLogPort):
        def log_login_attempt(self, attempt: LoginAttempt) -> None:
            pass

    class _FakeClock(Clock):
        def utc_now(self) -> datetime:
            return datetime(2024, 1, 1, tzinfo=timezone.utc)

    class _InMemRepo(UserAccountRepository):
        def __init__(self) -> None:
            now = datetime(2024, 1, 1, tzinfo=timezone.utc)
            self._account = Account(
                account_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                email=Email("admin@empresa.com"),
                password_hash="hashed:admin",
                role=AccountRole.ADMIN,
                active=True,
                must_change_password=must_change_password,
                failed_login_attempts=0,
                locked_until=None,
                token_version=0,
                created_at=now,
                updated_at=now,
            )

        def find_by_email(self, email: str) -> Optional[Account]:
            if self._account.email.value == email.lower().strip():
                return self._account
            return None

        def find_by_id(self, account_id: uuid.UUID) -> Optional[Account]:
            if self._account.account_id == account_id:
                return self._account
            return None

        def save(self, account: Account) -> None:
            self._account = account

        def increment_failed_attempts(self, account_id: uuid.UUID, locked_until: Optional[datetime]) -> None:
            pass

        def reset_failed_attempts(self, account_id: uuid.UUID) -> None:
            pass

        def bootstrap_admin(self, email: str, password_hash: str, role: str) -> str:
            return "preserved"

        def record_login_attempt(self, attempt: LoginAttempt) -> None:
            pass

    app = FastAPI()
    register_error_handlers(app)

    clock = _FakeClock()
    token_svc = JwtTokenService(
        secret_key="test-secret",
        issuer="test-issuer",
        audience="test-audience",
        clock=clock,
    )
    repo = _InMemRepo()
    hasher = _FakeHasher()

    app.state.token_svc = token_svc
    app.state.account_repo = repo
    app.state.clock = clock

    from application.use_cases.change_initial_password import ChangeInitialPassword
    from adapters.http.change_password_controller import router as cp_router

    use_case = ChangeInitialPassword(repo=repo, hasher=hasher)
    app.state.change_initial_password = use_case
    app.include_router(cp_router, prefix="/auth")
    return app


@pytest.fixture()
def client_must_change() -> TestClient:
    return TestClient(_make_app(must_change_password=True))


@pytest.fixture()
def client_no_change() -> TestClient:
    return TestClient(_make_app(must_change_password=False))


@pytest.fixture()
def valid_token() -> str:
    return _make_token(must_change_password=True)


@pytest.mark.contract
class TestChangeInitialPasswordContract200:
    def test_valid_change_returns_200(
        self, client_must_change: TestClient, valid_token: str
    ) -> None:
        response = client_must_change.post(
            "/auth/change-initial-password",
            json={"current_password": "admin", "new_password": "NewPass123"},
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 200


@pytest.mark.contract
class TestChangeInitialPasswordContract401:
    def test_missing_token_returns_401(self, client_must_change: TestClient) -> None:
        response = client_must_change.post(
            "/auth/change-initial-password",
            json={"current_password": "admin", "new_password": "NewPass123"},
        )
        assert response.status_code == 401

    def test_wrong_current_password_returns_401(
        self, client_must_change: TestClient, valid_token: str
    ) -> None:
        response = client_must_change.post(
            "/auth/change-initial-password",
            json={"current_password": "wrong", "new_password": "NewPass123"},
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 401


@pytest.mark.contract
class TestChangeInitialPasswordContract409:
    def test_account_not_requiring_change_returns_409(
        self, client_no_change: TestClient
    ) -> None:
        token = _make_token(must_change_password=False)
        response = client_no_change.post(
            "/auth/change-initial-password",
            json={"current_password": "admin", "new_password": "NewPass123"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409
