"""End-to-end integration test: login + change-initial-password + /auth/me flow.

Uses the full FastAPI app wired with in-memory fakes to simulate:
  1. POST /auth/login → 200 with must_change_password=True
  2. POST /auth/change-initial-password → 200
  3. GET /auth/me → 200 with must_change_password=False

Also validates that a stale token (old token_version) is rejected on /auth/me.

TDD: written as part of the Polish phase (T050).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest
import jwt as pyjwt
from fastapi import FastAPI
from fastapi.testclient import TestClient

from domain.entities.account import Account, AccountRole, AuthSession, Email, LoginAttempt
from application.ports.auth_ports import (
    AuditLogPort,
    Clock,
    PasswordHasher,
    TokenService,
    UnitOfWork,
    UserAccountRepository,
)
from adapters.http.error_handlers import register_error_handlers
from application.use_cases.authenticate_user import AuthenticateUser
from application.use_cases.change_initial_password import ChangeInitialPassword


# ── Shared fakes ──────────────────────────────────────────────────────────────

_FIXED_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
_ADMIN_ID = uuid.uuid4()
_JWT_SECRET = "e2e-test-secret"
_JWT_ISSUER = "test-issuer"
_JWT_AUDIENCE = "test-audience"


class _FixedClock(Clock):
    def utc_now(self) -> datetime:
        return _FIXED_NOW


class _FakeHasher(PasswordHasher):
    def hash(self, plain: str) -> str:
        return f"hashed:{plain}"

    def verify(self, plain: str, hashed: str) -> bool:
        return hashed == f"hashed:{plain}"


class _FakeAudit(AuditLogPort):
    def log_login_attempt(self, attempt: LoginAttempt) -> None:
        pass


class _FakeUoW(UnitOfWork):
    def __enter__(self) -> "UnitOfWork":
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


class _InMemoryAccountRepo(UserAccountRepository):
    """Mutable in-memory store for E2E flow testing."""

    def __init__(self) -> None:
        self._store: dict[str, Account] = {}
        now = _FIXED_NOW
        initial = Account(
            account_id=_ADMIN_ID,
            email=Email("admin@example.com"),
            password_hash="hashed:admin",
            role=AccountRole.ADMIN,
            active=True,
            failed_login_attempts=0,
            locked_until=None,
            must_change_password=True,
            token_version=1,
            created_at=now,
            updated_at=now,
        )
        self._store[initial.email.value] = initial

    def find_by_email(self, email: str) -> Optional[Account]:
        return self._store.get(email.strip().lower())

    def find_by_id(self, account_id: uuid.UUID) -> Optional[Account]:
        for account in self._store.values():
            if account.account_id == account_id:
                return account
        return None

    def save(self, account: Account) -> None:
        self._store[account.email.value] = account

    def increment_failed_attempts(
        self, account_id: uuid.UUID, locked_until: Optional[datetime]
    ) -> None:
        account = self.find_by_id(account_id)
        if account:
            import dataclasses
            updated = dataclasses.replace(
                account,
                failed_login_attempts=account.failed_login_attempts + 1,
                locked_until=locked_until,
            )
            self._store[updated.email.value] = updated

    def reset_failed_attempts(self, account_id: uuid.UUID) -> None:
        account = self.find_by_id(account_id)
        if account:
            import dataclasses
            updated = dataclasses.replace(
                account,
                failed_login_attempts=0,
                locked_until=None,
            )
            self._store[updated.email.value] = updated

    def bootstrap_admin(self, email: str, password_hash: str, role: str) -> str:
        return "preserved"

    def record_login_attempt(self, attempt: LoginAttempt) -> None:
        pass


class _RealLikeTokenSvc(TokenService):
    """Generates and validates real JWTs for E2E testing."""

    def create_access_token(
        self,
        account_id: uuid.UUID,
        role: str,
        must_change_password: bool,
        token_version: int,
    ) -> AuthSession:
        now = _FIXED_NOW
        expires_at = now + timedelta(minutes=30)
        payload = {
            "sub": str(account_id),
            "iss": _JWT_ISSUER,
            "aud": _JWT_AUDIENCE,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "role": role,
            "must_change_password": must_change_password,
            "token_version": token_version,
        }
        token = pyjwt.encode(payload, _JWT_SECRET, algorithm="HS256")
        return AuthSession(
            account_id=account_id,
            access_token=token,
            issued_at=now,
            expires_at=expires_at,
            must_change_password=must_change_password,
        )

    def decode_access_token(self, token: str) -> dict:  # type: ignore[override]
        return pyjwt.decode(
            token,
            _JWT_SECRET,
            algorithms=["HS256"],
            audience=_JWT_AUDIENCE,
            issuer=_JWT_ISSUER,
        )


def _make_e2e_app(repo: _InMemoryAccountRepo) -> FastAPI:
    from adapters.http.auth_controller import router as auth_router
    from adapters.http.identity_controller import router as identity_router
    from adapters.http.change_password_controller import router as change_pwd_router

    app = FastAPI()
    register_error_handlers(app)

    hasher = _FakeHasher()
    clock = _FixedClock()
    token_svc = _RealLikeTokenSvc()
    audit = _FakeAudit()

    app.state.authenticate_user = AuthenticateUser(
        repo=repo, hasher=hasher, token_svc=token_svc, clock=clock, audit_log=audit
    )
    app.state.change_initial_password = ChangeInitialPassword(repo=repo, hasher=hasher)
    app.state.account_repo = repo
    app.state.token_svc = token_svc
    app.state.clock = clock

    app.include_router(auth_router, prefix="/auth")
    app.include_router(identity_router, prefix="/auth")
    app.include_router(change_pwd_router, prefix="/auth")
    return app


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestE2ELoginAndPasswordChange:
    """Full-stack: login → change password → identity check."""

    def setup_method(self) -> None:
        self._repo = _InMemoryAccountRepo()
        self.client = TestClient(_make_e2e_app(self._repo), raise_server_exceptions=False)

    def test_login_returns_must_change_password_true(self) -> None:
        resp = self.client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "admin"},
        )
        assert resp.status_code == 200
        assert resp.json()["must_change_password"] is True

    def test_full_flow_login_change_me(self) -> None:
        # Step 1: Login
        resp = self.client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "admin"},
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        assert resp.json()["must_change_password"] is True

        # Step 2: Change initial password
        resp = self.client.post(
            "/auth/change-initial-password",
            json={"current_password": "admin", "new_password": "NewStrongPass1"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        # Step 3: Login again with new password to get fresh token
        resp = self.client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "NewStrongPass1"},
        )
        assert resp.status_code == 200
        new_token = resp.json()["access_token"]
        assert resp.json()["must_change_password"] is False

        # Step 4: Verify identity with new token
        resp = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {new_token}"},
        )
        assert resp.status_code == 200
        identity = resp.json()
        assert identity["email"] == "admin@example.com"
        assert identity["must_change_password"] is False

    def test_stale_token_rejected_after_password_change(self) -> None:
        # Login to get initial token
        resp = self.client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "admin"},
        )
        old_token = resp.json()["access_token"]

        # Change password — increments token_version
        self.client.post(
            "/auth/change-initial-password",
            json={"current_password": "admin", "new_password": "NewStrongPass1"},
            headers={"Authorization": f"Bearer {old_token}"},
        )

        # Old token must be rejected on /auth/me
        resp = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {old_token}"},
        )
        assert resp.status_code == 401

    def test_cannot_change_password_twice_with_same_token(self) -> None:
        resp = self.client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "admin"},
        )
        token = resp.json()["access_token"]

        # First change succeeds
        resp = self.client.post(
            "/auth/change-initial-password",
            json={"current_password": "admin", "new_password": "NewStrongPass1"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        # Second change attempt with same token → 409 (no longer requires change)
        # Note: token_version mismatch would actually give 401, but let's validate
        # that the state machine prevents re-change
        resp = self.client.post(
            "/auth/change-initial-password",
            json={"current_password": "NewStrongPass1", "new_password": "AnotherPass9"},
            headers={"Authorization": f"Bearer {token}"},
        )
        # Either 401 (stale token) or 409 (no change required) are acceptable
        assert resp.status_code in (401, 409)
