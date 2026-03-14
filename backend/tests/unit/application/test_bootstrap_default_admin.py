"""Unit tests for the BootstrapDefaultAdmin use case.

TDD: written before implementation (T031).
Covers create, preserve and recover (reactivate + force-reset) flows.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import pytest

from domain.entities.account import Account, AccountRole, Email, LoginAttempt
from application.ports.auth_ports import UserAccountRepository, PasswordHasher


# ── Fakes ─────────────────────────────────────────────────────────────────────

class FakeHasher(PasswordHasher):
    def hash(self, plain: str) -> str:
        return f"hashed:{plain}"

    def verify(self, plain: str, hashed: str) -> bool:
        return hashed == f"hashed:{plain}"


class FakeBootstrapRepo(UserAccountRepository):
    """In-memory repo that tracks bootstrap calls."""

    def __init__(self, existing: Optional[Account] = None) -> None:
        self._account: Optional[Account] = existing
        self.bootstrap_calls: list[dict[str, str]] = []

    def find_by_email(self, email: str) -> Optional[Account]:
        if self._account and self._account.email.value == email.lower().strip():
            return self._account
        return None

    def find_by_id(self, account_id: uuid.UUID) -> Optional[Account]:
        if self._account and self._account.account_id == account_id:
            return self._account
        return None

    def save(self, account: Account) -> None:
        self._account = account

    def increment_failed_attempts(
        self, account_id: uuid.UUID, locked_until: Optional[datetime]
    ) -> None:
        pass

    def reset_failed_attempts(self, account_id: uuid.UUID) -> None:
        pass

    def bootstrap_admin(self, email: str, password_hash: str, role: str) -> str:
        self.bootstrap_calls.append(
            {"email": email, "password_hash": password_hash, "role": role}
        )
        if self._account is None:
            return "created"
        if not self._account.active:
            return "reactivated"
        return "preserved"

    def record_login_attempt(self, attempt: LoginAttempt) -> None:
        pass


def _make_active_admin(email: str = "admin@empresa.com") -> Account:
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return Account(
        account_id=uuid.uuid4(),
        email=Email(email),
        password_hash="hashed:admin",
        role=AccountRole.ADMIN,
        active=True,
        must_change_password=False,
        failed_login_attempts=0,
        locked_until=None,
        token_version=0,
        created_at=now,
        updated_at=now,
    )


def _make_inactive_admin(email: str = "admin@empresa.com") -> Account:
    acc = _make_active_admin(email)
    # Manually create an inactive copy
    from dataclasses import replace
    return Account(
        account_id=acc.account_id,
        email=acc.email,
        password_hash=acc.password_hash,
        role=acc.role,
        active=False,         # ← inactive
        must_change_password=acc.must_change_password,
        failed_login_attempts=acc.failed_login_attempts,
        locked_until=acc.locked_until,
        token_version=acc.token_version,
        created_at=acc.created_at,
        updated_at=acc.updated_at,
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestBootstrapDefaultAdminCreate:
    def test_creates_admin_when_no_account_exists(self) -> None:
        """When no admin exists, the use case creates one."""
        from application.use_cases.bootstrap_default_admin import BootstrapDefaultAdmin

        repo = FakeBootstrapRepo(existing=None)
        use_case = BootstrapDefaultAdmin(repo=repo, hasher=FakeHasher())

        event = use_case.execute(
            email="admin@empresa.com", initial_password="admin"
        )

        assert event.action == "created"
        assert event.target_email == "admin@empresa.com"
        assert event.requires_password_reset is True
        assert len(repo.bootstrap_calls) == 1

    def test_created_account_has_must_change_password_true(self) -> None:
        """Bootstrap sets must_change_password=True on newly created account."""
        from application.use_cases.bootstrap_default_admin import BootstrapDefaultAdmin

        repo = FakeBootstrapRepo(existing=None)
        use_case = BootstrapDefaultAdmin(repo=repo, hasher=FakeHasher())

        event = use_case.execute(email="admin@empresa.com", initial_password="admin")

        assert event.requires_password_reset is True


@pytest.mark.unit
class TestBootstrapDefaultAdminPreserve:
    def test_preserves_existing_active_admin(self) -> None:
        """When an active admin already exists, no duplicate is created."""
        from application.use_cases.bootstrap_default_admin import BootstrapDefaultAdmin

        repo = FakeBootstrapRepo(existing=_make_active_admin())
        use_case = BootstrapDefaultAdmin(repo=repo, hasher=FakeHasher())

        event = use_case.execute(email="admin@empresa.com", initial_password="admin")

        assert event.action == "preserved"

    def test_idempotent_on_repeated_calls(self) -> None:
        """Calling bootstrap twice does not change the action to 'created'."""
        from application.use_cases.bootstrap_default_admin import BootstrapDefaultAdmin

        repo = FakeBootstrapRepo(existing=_make_active_admin())
        use_case = BootstrapDefaultAdmin(repo=repo, hasher=FakeHasher())

        event1 = use_case.execute(email="admin@empresa.com", initial_password="admin")
        event2 = use_case.execute(email="admin@empresa.com", initial_password="admin")

        assert event1.action == "preserved"
        assert event2.action == "preserved"


@pytest.mark.unit
class TestBootstrapDefaultAdminRecover:
    def test_reactivates_inactive_account(self) -> None:
        """Inactive admin account is reactivated and flagged for password reset."""
        from application.use_cases.bootstrap_default_admin import BootstrapDefaultAdmin

        repo = FakeBootstrapRepo(existing=_make_inactive_admin())
        use_case = BootstrapDefaultAdmin(repo=repo, hasher=FakeHasher())

        event = use_case.execute(email="admin@empresa.com", initial_password="admin")

        assert event.action == "reactivated"
        assert event.requires_password_reset is True
