"""Unit tests for ChangeInitialPassword use case.

TDD: written before implementation (T033).
Explicitly tests FR-009A: the admin initial password may be reused
after the mandatory change (no password history restriction).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import pytest

from domain.entities.account import Account, AccountRole, Email, LoginAttempt
from application.ports.auth_ports import UserAccountRepository, PasswordHasher


# ── Fakes ─────────────────────────────────────────────────────────────────────

class _FakeHasher(PasswordHasher):
    def hash(self, plain: str) -> str:
        return f"hashed:{plain}"

    def verify(self, plain: str, hashed: str) -> bool:
        return hashed == f"hashed:{plain}"


class _FakeRepo(UserAccountRepository):
    def __init__(self, account: Account) -> None:
        self._account = account

    def find_by_email(self, email: str) -> Optional[Account]:
        return self._account

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


def _provisioned_admin() -> Account:
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return Account(
        account_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        email=Email("admin@empresa.com"),
        password_hash="hashed:admin",
        role=AccountRole.ADMIN,
        active=True,
        must_change_password=True,   # ← provisioned state
        failed_login_attempts=0,
        locked_until=None,
        token_version=0,
        created_at=now,
        updated_at=now,
    )


def _active_admin() -> Account:
    acc = _provisioned_admin()
    return Account(
        account_id=acc.account_id,
        email=acc.email,
        password_hash=acc.password_hash,
        role=acc.role,
        active=acc.active,
        must_change_password=False,  # ← already changed
        failed_login_attempts=acc.failed_login_attempts,
        locked_until=acc.locked_until,
        token_version=acc.token_version,
        created_at=acc.created_at,
        updated_at=acc.updated_at,
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestChangeInitialPasswordSuccess:
    def test_clears_must_change_password_flag_on_success(self) -> None:
        """After a valid change, must_change_password becomes False."""
        from application.use_cases.change_initial_password import ChangeInitialPassword

        account = _provisioned_admin()
        repo = _FakeRepo(account)
        use_case = ChangeInitialPassword(repo=repo, hasher=_FakeHasher())

        use_case.execute(
            account_id=account.account_id,
            current_password="admin",
            new_password="NewPass123",
        )

        saved = repo.find_by_id(account.account_id)
        assert saved is not None
        assert saved.must_change_password is False

    def test_updates_password_hash(self) -> None:
        """The stored password_hash is updated to the new password's hash."""
        from application.use_cases.change_initial_password import ChangeInitialPassword

        account = _provisioned_admin()
        repo = _FakeRepo(account)
        use_case = ChangeInitialPassword(repo=repo, hasher=_FakeHasher())

        use_case.execute(
            account_id=account.account_id,
            current_password="admin",
            new_password="NewPass123",
        )

        saved = repo.find_by_id(account.account_id)
        assert saved is not None
        hasher = _FakeHasher()
        assert hasher.verify("NewPass123", saved.password_hash) is True

    def test_increments_token_version_on_password_change(self) -> None:
        """token_version is incremented to invalidate existing tokens."""
        from application.use_cases.change_initial_password import ChangeInitialPassword

        account = _provisioned_admin()
        original_version = account.token_version
        repo = _FakeRepo(account)
        use_case = ChangeInitialPassword(repo=repo, hasher=_FakeHasher())

        use_case.execute(
            account_id=account.account_id,
            current_password="admin",
            new_password="NewPass123",
        )

        saved = repo.find_by_id(account.account_id)
        assert saved is not None
        assert saved.token_version == original_version + 1


@pytest.mark.unit
class TestChangeInitialPasswordFR009A:
    def test_allows_reuse_of_initial_admin_password_after_mandatory_change(
        self,
    ) -> None:
        """FR-009A: admin can set password back to 'admin' after mandatory change.

        No password history restriction is applied.
        """
        from application.use_cases.change_initial_password import ChangeInitialPassword

        # Account in provisioned state (must_change_password=True)
        account = _provisioned_admin()
        repo = _FakeRepo(account)
        use_case = ChangeInitialPassword(repo=repo, hasher=_FakeHasher())

        # Change to a new password first (completing the mandatory change)
        use_case.execute(
            account_id=account.account_id,
            current_password="admin",
            new_password="Interim123",
        )

        # Now the account is in Active state
        saved = repo.find_by_id(account.account_id)
        assert saved is not None
        assert saved.must_change_password is False

        # FR-009A: reuse of original "admin" password must be allowed
        # (no exception should be raised)
        use_case.execute(
            account_id=account.account_id,
            current_password="Interim123",
            new_password="admin",  # reuse of initial password
        )

        final = repo.find_by_id(account.account_id)
        assert final is not None
        assert _FakeHasher().verify("admin", final.password_hash) is True


@pytest.mark.unit
class TestChangeInitialPasswordErrors:
    def test_raises_when_account_does_not_require_change(self) -> None:
        """Raises conflict error when must_change_password is already False."""
        from application.use_cases.change_initial_password import ChangeInitialPassword

        account = _active_admin()
        repo = _FakeRepo(account)
        use_case = ChangeInitialPassword(repo=repo, hasher=_FakeHasher())

        with pytest.raises(Exception) as exc_info:
            use_case.execute(
                account_id=account.account_id,
                current_password="admin",
                new_password="NewPass123",
            )
        assert "409" in str(exc_info.value) or "change" in str(exc_info.value).lower()

    def test_raises_on_wrong_current_password(self) -> None:
        """Wrong current password raises AuthenticationError."""
        from application.use_cases.change_initial_password import ChangeInitialPassword
        from adapters.http.error_handlers import AuthenticationError

        account = _provisioned_admin()
        repo = _FakeRepo(account)
        use_case = ChangeInitialPassword(repo=repo, hasher=_FakeHasher())

        with pytest.raises(AuthenticationError):
            use_case.execute(
                account_id=account.account_id,
                current_password="wrong",
                new_password="NewPass123",
            )
