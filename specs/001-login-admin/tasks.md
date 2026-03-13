# Tasks: Pagina de Login com Admin Inicial

**Input**: Design documents from `/specs/001-login-admin/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/openapi.yaml, quickstart.md

**Tests**: Tests are REQUIRED by constitution and by this feature plan. Every user story includes failing tests before implementation.

**Organization**: Tasks are grouped by user story to preserve independent implementation and validation.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize repository structure and baseline tooling for backend/frontend and SQL assets.

- [ ] T001 Create backend and frontend base directories in backend/src/ and frontend/src/
- [ ] T002 Initialize Python project metadata and dependencies in backend/pyproject.toml
- [ ] T003 [P] Configure strict typing and linting in backend/mypy.ini
- [ ] T004 [P] Configure pytest suites for unit, contract, and integration tests in backend/pytest.ini
- [ ] T005 [P] Initialize ReactJS + TypeScript project with Vite in frontend/package.json
- [ ] T006 [P] Configure frontend tests with Vitest and React Testing Library in frontend/vitest.config.ts
- [ ] T007 Create SQL migration and fixture directories in sql/migrations/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build core architecture, abstractions, and shared auth infrastructure required by all stories.

**⚠️ CRITICAL**: No user story work starts before this phase is complete.

- [ ] T008 Create domain base models and value objects in backend/src/domain/entities/account.py
- [ ] T009 [P] Define application ports for repository, token, hasher, clock, and audit in backend/src/application/ports/auth_ports.py
- [ ] T010 [P] Implement psycopg connection pool and unit-of-work adapter in backend/src/adapters/persistence/postgres_uow.py
- [ ] T011 [P] Implement JWT token service adapter contract and skeleton in backend/src/adapters/security/jwt_token_service.py
- [ ] T012 [P] Implement Argon2 password hasher adapter in backend/src/adapters/security/argon2_password_hasher.py
- [ ] T013 Create initial SQL schema for accounts and login attempts in sql/migrations/001_auth_base.sql
- [ ] T014 Implement FastAPI app composition root and dependency wiring in backend/src/bootstrap/app_factory.py
- [ ] T015 Configure shared exception mapping and HTTP error envelope in backend/src/adapters/http/error_handlers.py

**Checkpoint**: Foundation complete. User story implementation can begin.

---

## Phase 3: User Story 1 - Autenticar acesso ao sistema (Priority: P1) 🎯 MVP

**Goal**: Provide login page and backend authentication flow for active accounts with valid credentials.

**Independent Test**: Open login page, authenticate with valid account, receive bearer token, and access protected identity endpoint.

### Tests for User Story 1 (write first, must fail first)

- [ ] T016 [P] [US1] Add unit tests for AuthenticateUser success and generic failure in backend/tests/unit/application/test_authenticate_user.py
- [ ] T017 [P] [US1] Add contract tests for POST /auth/login success and 401 generic failure in backend/tests/contract/test_auth_login_contract.py
- [ ] T018 [P] [US1] Add integration tests for account lookup and password verification with PostgreSQL in backend/tests/integration/persistence/test_account_repository_login.py
- [ ] T019 [P] [US1] Add frontend integration test for login form submit flow in frontend/tests/integration/test_login_page_flow.ts

### Implementation for User Story 1

- [ ] T020 [P] [US1] Implement account repository read methods for login in backend/src/adapters/persistence/account_repository.py
- [ ] T021 [P] [US1] Implement AuthenticateUser use case in backend/src/application/use_cases/authenticate_user.py
- [ ] T022 [US1] Implement POST /auth/login endpoint controller in backend/src/adapters/http/auth_controller.py
- [ ] T023 [US1] Implement GET /auth/me protected endpoint in backend/src/adapters/http/identity_controller.py
- [ ] T024 [US1] Implement React login page and Axios API client integration in frontend/src/pages/login_page.tsx
- [ ] T025 [US1] Refine typing, validation, and error message consistency for login flow in backend/src/application/dto/auth_dto.py

**Checkpoint**: User Story 1 delivers an independently testable MVP.

---

## Phase 4: User Story 2 - Provisionar administrador inicial (Priority: P2)

**Goal**: Ensure idempotent bootstrap of admin@empresa.com with recovery of inactive/inconsistent state and mandatory initial password change.

**Independent Test**: Start with empty or inconsistent admin state, run bootstrap, verify single admin account and required initial password change behavior.

### Tests for User Story 2 (write first, must fail first)

- [ ] T026 [P] [US2] Add unit tests for BootstrapDefaultAdmin create and recover flows in backend/tests/unit/application/test_bootstrap_default_admin.py
- [ ] T027 [P] [US2] Add integration tests for idempotent bootstrap under PostgreSQL constraints in backend/tests/integration/persistence/test_bootstrap_admin_repository.py
- [ ] T028 [P] [US2] Add contract tests for POST /auth/change-initial-password in backend/tests/contract/test_change_initial_password_contract.py

### Implementation for User Story 2

- [ ] T029 [P] [US2] Implement repository write methods for bootstrap and recovery in backend/src/adapters/persistence/account_repository_bootstrap.py
- [ ] T030 [US2] Implement BootstrapDefaultAdmin use case in backend/src/application/use_cases/bootstrap_default_admin.py
- [ ] T031 [US2] Implement startup bootstrap trigger in backend/src/bootstrap/startup.py
- [ ] T032 [US2] Implement ChangeInitialPassword use case in backend/src/application/use_cases/change_initial_password.py
- [ ] T033 [US2] Implement POST /auth/change-initial-password endpoint in backend/src/adapters/http/change_password_controller.py
- [ ] T034 [US2] Implement React initial password change flow in frontend/src/pages/change_initial_password_page.tsx

**Checkpoint**: User Story 2 works independently and preserves one recoverable bootstrap admin account.

---

## Phase 5: User Story 3 - Tratar falhas de autenticacao com seguranca (Priority: P3)

**Goal**: Enforce lockout policy after 5 consecutive failures for 15 minutes with safe messaging and counter reset rules.

**Independent Test**: Trigger repeated invalid logins, observe lockout and generic responses, then verify counter reset after success or lock expiry.

### Tests for User Story 3 (write first, must fail first)

- [ ] T035 [P] [US3] Add unit tests for lockout and counter reset policy in backend/tests/unit/domain/test_login_attempt_policy.py
- [ ] T036 [P] [US3] Add contract tests for 423 locked response behavior in backend/tests/contract/test_auth_lockout_contract.py
- [ ] T037 [P] [US3] Add integration tests for failed attempt counter and locked_until updates in backend/tests/integration/persistence/test_login_lockout_repository.py
- [ ] T038 [P] [US3] Add frontend integration tests for lockout feedback on login page in frontend/tests/integration/test_login_lockout_feedback.ts

### Implementation for User Story 3

- [ ] T039 [P] [US3] Implement lockout policy service in backend/src/domain/services/login_attempt_policy.py
- [ ] T040 [US3] Extend repository methods for failed attempt increment and reset in backend/src/adapters/persistence/account_repository_lockout.py
- [ ] T041 [US3] Update AuthenticateUser use case with 5-fail and 15-minute lock rules in backend/src/application/use_cases/authenticate_user.py
- [ ] T042 [US3] Update login endpoint response mapping for locked state in backend/src/adapters/http/auth_controller.py
- [ ] T043 [US3] Add audit logging for login failure, lock, and unlock outcomes in backend/src/adapters/observability/audit_logger.py
- [ ] T044 [US3] Update React login UX for generic failure and temporary lock states in frontend/src/components/login_feedback.tsx

**Checkpoint**: User Story 3 enforces secure failure handling with independent verification.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final hardening, documentation alignment, and complete quickstart validation across all stories.

- [ ] T045 [P] Update OpenAPI contract details to match implemented responses in specs/001-login-admin/contracts/openapi.yaml
- [ ] T046 [P] Add backend end-to-end happy path integration test for login + password change + /auth/me in backend/tests/integration/api/test_auth_e2e.py
- [ ] T047 [P] Add SQL fixture for reproducible auth test data in sql/fixtures/auth_seed.sql
- [ ] T048 [P] Add frontend unit tests for core auth components in frontend/tests/unit/test_auth_components.tsx
- [ ] T049 Perform strict typing and test suite hardening updates in backend/pyproject.toml
- [ ] T050 Update quickstart execution notes with actual commands and checkpoints in specs/001-login-admin/quickstart.md
- [ ] T051 Run quickstart validation checklist and document result in specs/001-login-admin/checklists/requirements.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user stories.
- **User Story Phases (Phase 3-5)**: Depend on Foundational completion.
- **Polish (Phase 6)**: Depends on the selected user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2; no dependency on other user stories.
- **US2 (P2)**: Starts after Phase 2; can run independently, but reuses US1 auth primitives when present.
- **US3 (P3)**: Starts after Phase 2; extends authentication rules and can proceed after US1 auth baseline.

### Within Each User Story

- Tests first and failing before implementation.
- Domain/application behavior before endpoint orchestration.
- Backend behavior before frontend wiring when API contracts are involved.
- Story refactor and typing conformance before story completion.

---

## Parallel Opportunities

- Setup parallel: `T003`, `T004`, `T005`, `T006`.
- Foundational parallel: `T009`, `T010`, `T011`, `T012`.
- US1 parallel: `T016`, `T017`, `T018`, `T019` and then `T020`, `T021`.
- US2 parallel: `T026`, `T027`, `T028` and then `T029` with `T032` after contracts stabilize.
- US3 parallel: `T035`, `T036`, `T037`, `T038` and then `T039` with `T040`.
- Polish parallel: `T045`, `T046`, `T047`, `T048`.

---

## Parallel Example: User Story 1

```bash
# Parallel test authoring (must fail first)
T016 backend/tests/unit/application/test_authenticate_user.py
T017 backend/tests/contract/test_auth_login_contract.py
T018 backend/tests/integration/persistence/test_account_repository_login.py
T019 frontend/tests/integration/test_login_page_flow.ts

# Parallel implementation tasks after failing tests exist
T020 backend/src/adapters/persistence/account_repository.py
T021 backend/src/application/use_cases/authenticate_user.py
```

## Parallel Example: User Story 2

```bash
# Parallel test authoring
T026 backend/tests/unit/application/test_bootstrap_default_admin.py
T027 backend/tests/integration/persistence/test_bootstrap_admin_repository.py
T028 backend/tests/contract/test_change_initial_password_contract.py

# Parallel implementation opportunities
T029 backend/src/adapters/persistence/account_repository_bootstrap.py
T032 backend/src/application/use_cases/change_initial_password.py
```

## Parallel Example: User Story 3

```bash
# Parallel test authoring
T035 backend/tests/unit/domain/test_login_attempt_policy.py
T036 backend/tests/contract/test_auth_lockout_contract.py
T037 backend/tests/integration/persistence/test_login_lockout_repository.py
T038 frontend/tests/integration/test_login_lockout_feedback.ts

# Parallel implementation opportunities
T039 backend/src/domain/services/login_attempt_policy.py
T040 backend/src/adapters/persistence/account_repository_lockout.py
```

---

## Implementation Strategy

### MVP First (US1)

1. Complete Phase 1 and Phase 2.
2. Deliver Phase 3 (US1) end-to-end.
3. Validate independent test criteria for US1 before progressing.

### Incremental Delivery

1. Add US2 for bootstrap admin provisioning and initial password change.
2. Add US3 for lockout and secure failure handling.
3. Finish with Polish phase and quickstart validation.

### Team Parallelization

1. Shared team completes Setup and Foundational phases.
2. After foundation:
   - Dev A: US1 backend + contract tests
   - Dev B: US1 frontend + UX tests
   - Dev C: Prepares US2 repository/integration scaffolding
3. After US1 baseline:
   - Dev A: US2 use cases
   - Dev B: US2 frontend password change flow
   - Dev C: US3 lockout behavior

---

## Notes

- Every task includes an explicit file path.
- `[P]` marks tasks that can run concurrently without conflicting incomplete dependencies.
- Story labels (`[US1]`, `[US2]`, `[US3]`) are included only in user story phases.
- Preserve strict typing and SOLID constraints while completing each task.
- Keep SQL explicit and native-driver based; do not introduce ORM abstractions.
