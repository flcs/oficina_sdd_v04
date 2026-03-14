"""Contract tests for POST /auth/login.

Validates HTTP-level contract:
  200 — valid credentials
  400 — invalid payload (missing/empty/malformed fields)
  401 — invalid credentials (neutral message, no account enumeration)

TDD: written before implementation of auth_controller.py (T022).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _make_app() -> object:
    """Build a minimal FastAPI app wired with fakes for contract testing."""
    import uuid
    from datetime import datetime, timedelta, timezone
    from typing import Optional

    from fastapi import FastAPI
    from domain.entities.account import Account, AccountRole, AuthSession, Email, LoginAttempt
    from application.ports.auth_ports import (
        UserAccountRepository,
        PasswordHasher,
        TokenService,
        Clock,
        AuditLogPort,
        UnitOfWork,
    )
    from adapters.http.error_handlers import register_error_handlers

    class _FakeClock(Clock):
        def utc_now(self) -> datetime:
            return datetime(2024, 1, 1, tzinfo=timezone.utc)

    class _FakeHasher(PasswordHasher):
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
            now = datetime(2024, 1, 1, tzinfo=timezone.utc)
            return AuthSession(
                account_id=account_id,
                access_token="test-token",
                issued_at=now,
                expires_at=now + timedelta(minutes=30),
                must_change_password=must_change_password,
            )

        def decode_access_token(self, token: str) -> dict[str, object]:
            return {}

    class _FakeAudit(AuditLogPort):
        def log_login_attempt(self, attempt: LoginAttempt) -> None:
            pass

    class _InMemRepo(UserAccountRepository):
        def __init__(self) -> None:
            now = datetime(2024, 1, 1, tzinfo=timezone.utc)
            active_account = Account(
                account_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                email=Email("valid@empresa.com"),
                password_hash="hashed:secret",
                role=AccountRole.USER,
                active=True,
                must_change_password=False,
                failed_login_attempts=0,
                locked_until=None,
                token_version=0,
                created_at=now,
                updated_at=now,
            )
            self._store: dict[str, Account] = {
                "valid@empresa.com": active_account
            }

        def find_by_email(self, email: str) -> Optional[Account]:
            return self._store.get(email.lower().strip())

        def find_by_id(self, account_id: uuid.UUID) -> Optional[Account]:
            return next(
                (a for a in self._store.values() if a.account_id == account_id),
                None,
            )

        def save(self, account: Account) -> None:
            self._store[account.email.value] = account

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

    app = FastAPI()
    register_error_handlers(app)

    # Wire the use case and controller directly
    from application.use_cases.authenticate_user import AuthenticateUser
    from adapters.http.auth_controller import router as auth_router

    repo = _InMemRepo()
    use_case = AuthenticateUser(
        repo=repo,
        hasher=_FakeHasher(),
        token_svc=_FakeTokenSvc(),
        clock=_FakeClock(),
        audit_log=_FakeAudit(),
    )
    app.state.authenticate_user = use_case
    app.include_router(auth_router, prefix="/auth")
    return app


@pytest.fixture()
def client() -> TestClient:
    from fastapi.testclient import TestClient as TC
    return TC(_make_app())  # type: ignore[arg-type]


@pytest.mark.contract
class TestLoginContract200:
    def test_valid_credentials_return_200_with_bearer_token(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/auth/login",
            json={"email": "valid@empresa.com", "password": "secret"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"


@pytest.mark.contract
class TestLoginContract400:
    def test_missing_email_returns_400(self, client: TestClient) -> None:
        response = client.post("/auth/login", json={"password": "secret"})
        assert response.status_code == 400

    def test_missing_password_returns_400(self, client: TestClient) -> None:
        response = client.post("/auth/login", json={"email": "a@b.com"})
        assert response.status_code == 400

    def test_empty_email_returns_400(self, client: TestClient) -> None:
        response = client.post("/auth/login", json={"email": "", "password": "x"})
        assert response.status_code == 400

    def test_empty_password_returns_400(self, client: TestClient) -> None:
        response = client.post(
            "/auth/login", json={"email": "valid@empresa.com", "password": ""}
        )
        assert response.status_code == 400

    def test_malformed_email_returns_400(self, client: TestClient) -> None:
        response = client.post(
            "/auth/login", json={"email": "not-an-email", "password": "x"}
        )
        assert response.status_code == 400

    def test_400_body_does_not_reveal_account_details(
        self, client: TestClient
    ) -> None:
        response = client.post("/auth/login", json={"email": "", "password": ""})
        assert response.status_code == 400
        body = response.json()
        assert "detail" in body
        assert "account" not in body["detail"].lower()
        assert "exist" not in body["detail"].lower()


@pytest.mark.contract
class TestLoginContract401:
    def test_wrong_password_returns_401(self, client: TestClient) -> None:
        response = client.post(
            "/auth/login",
            json={"email": "valid@empresa.com", "password": "wrong"},
        )
        assert response.status_code == 401

    def test_unknown_email_returns_401(self, client: TestClient) -> None:
        response = client.post(
            "/auth/login",
            json={"email": "nobody@empresa.com", "password": "any"},
        )
        assert response.status_code == 401

    def test_401_body_is_neutral(self, client: TestClient) -> None:
        response = client.post(
            "/auth/login",
            json={"email": "nobody@empresa.com", "password": "any"},
        )
        assert response.status_code == 401
        body = response.json()
        assert "detail" in body
        assert "account" not in body["detail"].lower()
        assert "exist" not in body["detail"].lower()
        assert "user" not in body["detail"].lower()
