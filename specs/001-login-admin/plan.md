# Implementation Plan: Pagina de Login com Admin Inicial

**Branch**: `001-login-admin` | **Date**: 2026-03-13 | **Spec**: `specs/001-login-admin/spec.md`
**Input**: Feature specification from `/specs/001-login-admin/spec.md`

## Summary

Entregar pagina de login em React + TypeScript integrada a um backend Python
com arquitetura hexagonal, bootstrap idempotente do admin
`admin@empresa.com`, troca obrigatoria de senha inicial, lockout por 5 falhas
em 15 minutos e respostas seguras: `400` para payload invalido, `401` para
falha de autenticacao e bloqueio, e `503` com `Retry-After` para
indisponibilidade temporaria de dependencia.

## Technical Context

**Language/Version**: Python 3.12 and TypeScript 5.x  
**Primary Dependencies**: FastAPI, Uvicorn, psycopg 3, psycopg_pool, PyJWT, argon2-cffi, Pydantic v2, pydantic-settings, React, Vite, React Router, Axios  
**Storage**: PostgreSQL 16+ via psycopg 3 with explicit SQL (no ORM)  
**Testing**: pytest (unit/integration/contract/performance), Vitest + React Testing Library  
**Target Platform**: Linux backend service and modern browsers  
**Project Type**: web application (backend + SPA frontend)  
**Performance Goals**: API login p95 < 300 ms (excluding network), token validation p95 < 100 ms, and end-to-end login journey measured to support SC-001 (95% <= 30 s)  
**Constraints**: OO design, dependency on abstractions, SOLID, strict typing, mandatory TDD, hexagonal architecture, repository pattern, JWT only in Authorization header, native PostgreSQL driver only, no ORM  
**Scale/Scope**: one authentication slice with login UI/API, bootstrap admin flow, mandatory initial password change, lockout and observability

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- PASS: Domain behavior is modeled with cohesive objects and explicit boundaries.
- PASS: Business rules rely on ports/abstractions; concrete adapters are wired only at composition root.
- PASS: SOLID and strict typing remain explicit across production code and tests.
- PASS: TDD order is preserved in tasks: tests first, then implementation, then refactor.
- PASS: No complexity exception is required for this feature.

**Post-Design Re-check**: PASS. `research.md`, `data-model.md`,
`contracts/openapi.yaml`, `quickstart.md`, and `tasks.md` are aligned with
the constitution and with the latest clarifications.

## Project Structure

### Documentation (this feature)

```text
specs/001-login-admin/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── domain/
│   │   ├── entities/
│   │   ├── value_objects/
│   │   └── services/
│   ├── application/
│   │   ├── dto/
│   │   ├── ports/
│   │   └── use_cases/
│   ├── adapters/
│   │   ├── http/
│   │   ├── persistence/
│   │   ├── security/
│   │   └── observability/
│   └── bootstrap/
└── tests/
    ├── contract/
    ├── integration/
    ├── performance/
    └── unit/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   ├── services/
│   └── styles/
└── tests/
    ├── integration/
    └── unit/

sql/
├── migrations/
└── fixtures/
```

**Structure Decision**: Web split with hexagonal backend and React SPA frontend.
Repository adapters isolate SQL; HTTP adapters map behavior to contract-safe
responses, including `503 + Retry-After` and neutral lockout semantics.

## Phase 0 Research Summary

- Decision: Keep lockout response semantics neutral and contract-tested without
  exposing account existence.
- Decision: Use `503 + Retry-After` for transient auth dependency failures.
- Decision: Validate `400` vs `401` at contract level and keep neutral messages.
- Decision: Allow future reuse of `admin` password after initial mandatory
  change, as clarified in spec.

## Phase 1 Design Summary

- `data-model.md` defines account, login attempt, session, and bootstrap event
  entities with lockout and password-change state transitions.
- `contracts/openapi.yaml` defines login/change-password/identity endpoints
  with explicit `400`, `401`, and `503` semantics.
- `quickstart.md` includes TDD flow and manual validation for lockout,
  temporary unavailability, and performance checkpoints.
- Tasks include dedicated coverage for SC-001 evidence and API latency checks.

## Complexity Tracking

Nenhuma violacao de constituicao identificada.
