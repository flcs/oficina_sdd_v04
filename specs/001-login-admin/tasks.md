# Tasks: Pagina de Login com Admin Inicial

**Input**: Design documents from `/specs/001-login-admin/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/openapi.yaml, quickstart.md

**Tests**: Tests are REQUIRED by constitution and by this feature plan. Every user story includes failing tests before implementation.

**Organization**: Tasks are grouped by user story to preserve independent implementation and validation.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize repository structure and baseline tooling for backend, frontend and SQL assets.

- [ ] T001 Create backend and frontend base directories in backend/src/ and frontend/src/
- [ ] T002 Initialize Python project metadata and dependencies in backend/pyproject.toml
- [ ] T003 [P] Configure strict typing and linting in backend/mypy.ini
- [ ] T004 [P] Configure pytest suites for unit, contract, integration and performance tests in backend/pytest.ini
- [ ] T005 [P] Initialize React + TypeScript project with Vite in frontend/package.json
- [ ] T006 [P] Configure frontend tests with Vitest and React Testing Library in frontend/vitest.config.ts
- [ ] T007 Create SQL migration and fixture directories in sql/migrations/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build core architecture, abstractions and shared auth infrastructure required by all stories.

**⚠️ CRITICAL**: No user story work starts before this phase is complete.

- [ ] T008 Create domain entities and value objects with lockout and password-change states in backend/src/domain/entities/account.py
- [ ] T009 [P] Define application ports for UserAccountRepository, PasswordHasher, TokenService, Clock, AuditLogPort and UnitOfWork in backend/src/application/ports/auth_ports.py
- [ ] T010 [P] Implement psycopg connection pool and unit-of-work adapter in backend/src/adapters/persistence/postgres_uow.py
- [ ] T011 [P] Implement JWT token service adapter with iss/aud/sub/exp/iat/jti and token_version invalidation in backend/src/adapters/security/jwt_token_service.py
- [ ] T012 [P] Implement Argon2id password hasher adapter in backend/src/adapters/security/argon2_password_hasher.py
- [ ] T013 Create initial SQL schema for accounts table with lockout columns and login_attempts table in sql/migrations/001_auth_base.sql
- [ ] T014 Implement FastAPI app composition root and dependency wiring in backend/src/bootstrap/app_factory.py
- [ ] T015 Configure shared exception mapping and neutral HTTP error envelope for 400/401/503 in backend/src/adapters/http/error_handlers.py

**Checkpoint**: Foundation complete. User story implementation can begin.

---

## Phase 3: User Story 1 - Autenticar acesso ao sistema (Priority: P1) 🎯 MVP

**Goal**: Provide login page and backend authentication flow for active accounts with valid credentials, returning JWT in Authorization header.

**Independent Test**: Open login page, submit valid credentials, receive bearer token, access protected /auth/me endpoint.

### Tests for User Story 1 (write first, must fail first)

- [ ] T016 [P] [US1] Add unit tests for AuthenticateUser use case covering success, invalid credentials and inactive account in backend/tests/unit/application/test_authenticate_user.py
- [ ] T017 [P] [US1] Add contract tests for POST /auth/login covering 200 success, 400 invalid payload and 401 invalid credentials in backend/tests/contract/test_auth_login_contract.py
- [ ] T018 [P] [US1] Add integration tests for account lookup and Argon2 password verification against PostgreSQL in backend/tests/integration/persistence/test_account_repository_login.py
- [ ] T019 [P] [US1] Add frontend integration test for login form submit, token receipt and redirect in frontend/tests/integration/test_login_page_flow.ts

### Implementation for User Story 1

- [ ] T020 [P] [US1] Implement account repository read methods for login in backend/src/adapters/persistence/account_repository.py
- [ ] T021 [P] [US1] Implement AuthenticateUser use case against ports abstractions in backend/src/application/use_cases/authenticate_user.py
- [ ] T022 [US1] Implement POST /auth/login controller with 400 input validation and 401 neutral response mapping in backend/src/adapters/http/auth_controller.py
- [ ] T023 [US1] Implement GET /auth/me protected endpoint with bearer token validation and account state recheck in backend/src/adapters/http/identity_controller.py
- [ ] T024 [US1] Implement LoginRequest and LoginSuccessResponse DTOs with strict typing in backend/src/application/dto/auth_dto.py
- [ ] T025 [US1] Implement React login page with Axios client, form validation and token storage in frontend/src/pages/login_page.tsx

**Checkpoint**: User Story 1 delivers an independently testable MVP.

---

## Phase 4: User Story 2 - Provisionar administrador inicial (Priority: P2)

**Goal**: Idempotent bootstrap of admin@empresa.com with recovery of inactive/inconsistent state and mandatory initial password change; admin password reuse explicitly allowed after first change (FR-009A).

**Independent Test**: Start with empty or inconsistent admin state, run bootstrap, verify single account, authenticate, reach forced password change flow.

### Tests for User Story 2 (write first, must fail first)

- [ ] T026 [P] [US2] Add unit tests for BootstrapDefaultAdmin covering create, preserve and recover flows in backend/tests/unit/application/test_bootstrap_default_admin.py
- [ ] T027 [P] [US2] Add integration tests for idempotent bootstrap and inactive-account recovery under PostgreSQL constraints in backend/tests/integration/persistence/test_bootstrap_admin_repository.py
- [ ] T028 [P] [US2] Add contract tests for POST /auth/change-initial-password covering 200, 401 and 409 scenarios in backend/tests/contract/test_change_initial_password_contract.py
- [ ] T029 [P] [US2] Add unit tests for ChangeInitialPassword use case including explicit allow of admin password reuse after mandatory change (FR-009A) in backend/tests/unit/application/test_change_initial_password.py

### Implementation for User Story 2

- [ ] T030 [P] [US2] Implement repository write methods for bootstrap create and inconsistent-account recovery in backend/src/adapters/persistence/account_repository_bootstrap.py
- [ ] T031 [US2] Implement BootstrapDefaultAdmin use case with idempotence using INSERT ON CONFLICT in backend/src/application/use_cases/bootstrap_default_admin.py
- [ ] T032 [US2] Implement startup bootstrap trigger wired into FastAPI lifespan in backend/src/bootstrap/startup.py
- [ ] T033 [US2] Implement ChangeInitialPassword use case with no password history restriction for admin reuse (FR-009A) in backend/src/application/use_cases/change_initial_password.py
- [ ] T034 [US2] Implement POST /auth/change-initial-password endpoint in backend/src/adapters/http/change_password_controller.py
- [ ] T035 [US2] Implement React initial password change page integrated with change-password API in frontend/src/pages/change_initial_password_page.tsx

**Checkpoint**: User Story 2 works independently and preserves one recoverable bootstrap admin account.

---

## Phase 5: User Story 3 - Tratar falhas de autenticacao com seguranca (Priority: P3)

**Goal**: Enforce lockout after 5 consecutive failures for 15 minutes with neutral responses, counter reset on success or expiry, and 503 + Retry-After for transient dependency failures.

**Independent Test**: Trigger five invalid logins, observe neutral lockout response; wait for expiry or succeed and confirm counter reset; simulate dependency unavailability and confirm 503 + Retry-After.

### Tests for User Story 3 (write first, must fail first)

- [ ] T036 [P] [US3] Add unit tests for LoginAttemptPolicy covering 5-fail threshold, 15-min block duration and counter reset conditions in backend/tests/unit/domain/test_login_attempt_policy.py
- [ ] T037 [P] [US3] Add contract tests for lockout with neutral 401 semantics confirming no account enumeration in backend/tests/contract/test_auth_lockout_contract.py
- [ ] T038 [P] [US3] Add contract tests for 503 + Retry-After header when auth service dependency is temporarily unavailable in backend/tests/contract/test_auth_unavailable_contract.py
- [ ] T039 [P] [US3] Add integration tests for failed_login_attempts increment, locked_until update and counter reset against PostgreSQL in backend/tests/integration/persistence/test_login_lockout_repository.py
- [ ] T040 [P] [US3] Add integration tests for temporary auth dependency unavailability and Retry-After propagation in backend/tests/integration/api/test_auth_unavailable_retry_after.py
- [ ] T041 [P] [US3] Add frontend integration tests for generic failure and lockout neutral feedback on login page in frontend/tests/integration/test_login_lockout_feedback.ts
- [ ] T042 [P] [US3] Add frontend integration test for neutral 503 display and retry guidance in frontend/tests/integration/test_login_unavailable_feedback.ts

### Implementation for User Story 3

- [ ] T043 [P] [US3] Implement LoginAttemptPolicy domain service with 5-fail/15-min/reset rules in backend/src/domain/services/login_attempt_policy.py
- [ ] T044 [US3] Extend account repository with failed attempt increment and counter reset methods in backend/src/adapters/persistence/account_repository_lockout.py
- [ ] T045 [US3] Update AuthenticateUser use case to enforce lockout policy via LoginAttemptPolicy port in backend/src/application/use_cases/authenticate_user.py
- [ ] T046 [US3] Update login endpoint to map locked account to neutral 401 and dependency failure to 503 + Retry-After in backend/src/adapters/http/auth_controller.py
- [ ] T047 [US3] Add audit logging adapter for login failure, lock start and lock release outcomes in backend/src/adapters/observability/audit_logger.py
- [ ] T048 [US3] Update React login feedback component to display neutral error, lockout and 503 + retry states in frontend/src/components/login_feedback.tsx

**Checkpoint**: User Story 3 enforces secure failure handling with independent verification.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final hardening, observability evidence, documentation alignment and quickstart validation across all stories.

- [ ] T049 [P] Update OpenAPI contract to match all implemented response codes and Retry-After header in specs/001-login-admin/contracts/openapi.yaml
- [ ] T050 [P] Add backend end-to-end integration test for full flow: login + change-password + /auth/me in backend/tests/integration/api/test_auth_e2e.py
- [ ] T051 [P] Add SQL fixture for reproducible auth test data covering active, locked and must-change-password accounts in sql/fixtures/auth_seed.sql
- [ ] T052 [P] Add frontend unit tests for LoginForm, LoginFeedback and ChangePasswordForm components in frontend/tests/unit/test_auth_components.tsx
- [ ] T053 [P] Implement backend metrics adapter for login journey timing (end-to-end from request to response) in backend/src/adapters/observability/login_metrics.py
- [ ] T054 [P] Add performance test validating API login p95 < 300 ms and token validation p95 < 100 ms to support SC-001 in backend/tests/integration/performance/test_login_latency.py
- [ ] T055 Perform strict typing audit and test suite hardening; update mypy and pytest configuration in backend/pyproject.toml
- [ ] T056 Update quickstart with actual commands, environment setup and validation checkpoints in specs/001-login-admin/quickstart.md
- [ ] T057 Run quickstart validation checklist and document results in specs/001-login-admin/checklists/requirements.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user stories.
- **User Story Phases (Phase 3-5)**: Depend on Foundational completion.
- **Polish (Phase 6)**: Depends on selected user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2; no dependency on other user stories.
- **US2 (P2)**: Starts after Phase 2; independent but reuses US1 auth primitives when present.
- **US3 (P3)**: Starts after Phase 2; extends US1 authentication rules; best started after US1 baseline.

### Within Each User Story

- Tests first and failing before any implementation starts.
- Domain/application behavior before HTTP endpoint orchestration.
- Backend behavior stable before frontend wiring is finalized.
- Typing conformance and SOLID review before checkpoint sign-off.

---

## Parallel Opportunities

- Setup parallel: `T003`, `T004`, `T005`, `T006`.
- Foundational parallel: `T009`, `T010`, `T011`, `T012`.
- US1 tests parallel: `T016`, `T017`, `T018`, `T019`.
- US1 impl parallel: `T020`, `T021` (then T022 after both complete).
- US2 tests parallel: `T026`, `T027`, `T028`, `T029`.
- US2 impl parallel: `T030` (can start with tests); `T033` after contracts stabilize.
- US3 tests parallel: `T036`, `T037`, `T038`, `T039`, `T040`, `T041`, `T042`.
- US3 impl parallel: `T043` with `T044`.
- Polish parallel: `T049`, `T050`, `T051`, `T052`, `T053`, `T054`.

---

## Parallel Example: User Story 1

```bash
# Parallel test authoring (must fail first)
T016 backend/tests/unit/application/test_authenticate_user.py
T017 backend/tests/contract/test_auth_login_contract.py
T018 backend/tests/integration/persistence/test_account_repository_login.py
T019 frontend/tests/integration/test_login_page_flow.ts

# Parallel implementation after failing tests exist
T020 backend/src/adapters/persistence/account_repository.py
T021 backend/src/application/use_cases/authenticate_user.py
```

## Parallel Example: User Story 2

```bash
# Parallel test authoring
T026 backend/tests/unit/application/test_bootstrap_default_admin.py
T027 backend/tests/integration/persistence/test_bootstrap_admin_repository.py
T028 backend/tests/contract/test_change_initial_password_contract.py
T029 backend/tests/unit/application/test_change_initial_password.py

# Parallel implementation opportunities
T030 backend/src/adapters/persistence/account_repository_bootstrap.py
T033 backend/src/application/use_cases/change_initial_password.py
```

## Parallel Example: User Story 3

```bash
# Parallel test authoring
T036 backend/tests/unit/domain/test_login_attempt_policy.py
T037 backend/tests/contract/test_auth_lockout_contract.py
T038 backend/tests/contract/test_auth_unavailable_contract.py
T039 backend/tests/integration/persistence/test_login_lockout_repository.py
T040 backend/tests/integration/api/test_auth_unavailable_retry_after.py
T041 frontend/tests/integration/test_login_lockout_feedback.ts
T042 frontend/tests/integration/test_login_unavailable_feedback.ts

# Parallel implementation opportunities
T043 backend/src/domain/services/login_attempt_policy.py
T044 backend/src/adapters/persistence/account_repository_lockout.py
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
3. Finish with Polish phase, observability evidence and quickstart validation.

### Team Parallelization

1. Shared team completes Setup and Foundational phases.
2. After foundation:
   - Dev A: US1 backend + contract tests
   - Dev B: US1 frontend + UX tests
   - Dev C: Prepares US2 repository/integration scaffolding
3. After US1 baseline:
   - Dev A: US2 use cases + bootstrap
   - Dev B: US2 frontend password change flow
   - Dev C: US3 lockout policy and tests

---

## Notes

- Every task includes an explicit file path.
- `[P]` marks tasks that can run concurrently without conflicting incomplete dependencies.
- Story labels (`[US1]`, `[US2]`, `[US3]`) are included only in user story phases.
- T022 creates `auth_controller.py` (US1); T046 extends it (US3) — execute in order.
- T033 incorporates FR-009A (no password history restriction) — no separate task needed.
- Preserve strict typing and SOLID constraints throughout every task.
- Keep SQL explicit and native-driver based; do not introduce ORM abstractions.
