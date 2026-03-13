# Implementation Plan: Pagina de Login com Admin Inicial

**Branch**: `001-login-admin` | **Date**: 2026-03-13 | **Spec**: [/Dados/Fernando/SDD/oficina_sdd_v04/specs/001-login-admin/spec.md](file:///Dados/Fernando/SDD/oficina_sdd_v04/specs/001-login-admin/spec.md)
**Input**: Feature specification from `/specs/001-login-admin/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Entregar uma pagina de login integrada a um servico de autenticacao em Python,
com bootstrap idempotente do administrador inicial `admin@empresa.com`,
bloqueio temporario por 5 falhas consecutivas e troca obrigatoria da senha
bootstrap no primeiro acesso. A abordagem tecnica usa Arquitetura Hexagonal,
padrao Repository sobre PostgreSQL com driver nativo psycopg 3, JWT no cabecalho
`Authorization`, e execucao orientada por TDD com suites unitarias, de contrato
e de integracao.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: FastAPI, Uvicorn, psycopg 3, psycopg_pool, PyJWT, argon2-cffi, Pydantic v2, pydantic-settings  
**Storage**: PostgreSQL 16+ accessed exclusively through psycopg 3 with explicit SQL and no ORM  
**Testing**: pytest, pytest-mock, httpx, unit tests for domain/application, contract tests for HTTP, integration tests with real PostgreSQL  
**Target Platform**: Linux server hosting a Python web application and browser-based login page
**Project Type**: web application with backend service plus thin frontend login experience  
**Performance Goals**: login p95 below 300 ms excluding network latency; bootstrap idempotence under concurrent startup; JWT validation on protected requests below 100 ms p95  
**Constraints**: Object-Oriented Design, dependency on abstractions, SOLID, strict typing, mandatory TDD, Hexagonal Architecture, Repository pattern, JWT only in Authorization header, native PostgreSQL driver only, no ORM  
**Scale/Scope**: single bounded auth slice covering one login page, auth API, bootstrap admin flow, initial password change flow, and lockout handling for the first release

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- PASS: O modelo de objetos fica separado em entidades de dominio, value
  objects, casos de uso e adaptadores HTTP/persistencia, sem orquestracao
  procedimental espalhada.
- PASS: Regras de autenticacao, lockout, bootstrap e troca obrigatoria de senha
  dependem apenas de portas abstratas (`UserAccountRepository`, `PasswordHasher`,
  `TokenService`, `Clock`, `AuditLogPort`, `UnitOfWork`).
- PASS: O impacto em SOLID e strict typing esta enderecado com contratos
  tipados em portas, DTOs de aplicacao e mapeamentos explicitos dos adapters.
- PASS: A estrategia de TDD esta definida com ordem obrigatoria de testes
  unitarios, de contrato e de integracao antes da implementacao minima.
- PASS: Nao ha desvios de complexidade sem justificativa; o uso de Repository e
  Hexagonal Architecture responde diretamente as restricoes do usuario e da
  constituicao.

**Post-Design Re-check**: PASS. `research.md`, `data-model.md`, `contracts/` e
`quickstart.md` mantem objetos coesos, dependencias por portas, Repository com
SQL explicito, JWT no cabecalho e sequenciamento TDD sem violacoes abertas da
constituicao.

## Project Structure

### Documentation (this feature)

```text
specs/001-login-admin/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
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
  └── unit/

frontend/
├── src/
│   ├── pages/
│   ├── components/
│   ├── services/
│   └── styles/
└── tests/
  └── integration/

sql/
├── migrations/
└── fixtures/
```

**Structure Decision**: Adotar uma estrutura web com `backend/` e `frontend/`.
O backend concentra o hexagono em Python; o frontend permanece fino, dedicado a
login, troca de senha inicial e consumo do servico de autenticacao. `sql/`
centraliza migrations e fixtures SQL puros, preservando o uso exclusivo do
driver nativo PostgreSQL.

## Complexity Tracking

> Nenhuma violacao da constituicao identificada.
