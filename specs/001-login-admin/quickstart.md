# Quickstart: Pagina de Login com Admin Inicial

## Objetivo

Executar e validar ponta a ponta o fluxo de autenticacao com:
- bootstrap do admin inicial
- login com JWT
- troca obrigatoria de senha no primeiro acesso
- lockout apos 5 falhas por 15 minutos
- resposta neutra em 401 e resposta 503 com `Retry-After`

## Pre-requisitos

- Python 3.12
- Node.js 22+ e npm
- PostgreSQL 14+
- Banco com permissao de criar schema/tabelas

## Estrutura esperada

- `backend/` API FastAPI
- `frontend/` SPA React + TypeScript
- `sql/migrations/001_auth_base.sql` schema base
- `sql/fixtures/auth_seed.sql` dados de fixture

## Variaveis de ambiente (backend)

Exporte estas variaveis antes de iniciar a API:

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/login_admin"
export JWT_SECRET_KEY="dev-secret-change-me"
export JWT_ISSUER="oficina_sdd"
export JWT_AUDIENCE="oficina_sdd_clients"
export BOOTSTRAP_ADMIN_EMAIL="admin@empresa.com"
export BOOTSTRAP_ADMIN_INITIAL_PASSWORD="admin"
```

## Setup do banco

```bash
psql "$DATABASE_URL" -f sql/migrations/001_auth_base.sql
psql "$DATABASE_URL" -f sql/fixtures/auth_seed.sql
```

## Setup e execucao do backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
PYTHONPATH=src uvicorn bootstrap.app_factory:create_app --factory --host 0.0.0.0 --port 8000
```

## Setup e execucao do frontend

Em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend esperado em `http://localhost:5173` com proxy para `http://localhost:8000`.

## Testes automatizados

### Backend

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=src pytest tests/unit
PYTHONPATH=src pytest tests/contract
PYTHONPATH=src pytest tests/integration
PYTHONPATH=src pytest tests/integration/performance
```

### Frontend

```bash
cd frontend
npm run test -- --run
```

## Validacao manual (checklist funcional)

1. Iniciar backend sem contas e confirmar bootstrap de `admin@empresa.com` ativo.
2. Fazer login com senha inicial e verificar `must_change_password=true`.
3. Chamar `POST /auth/change-initial-password` e confirmar `200`.
4. Fazer novo login com senha alterada e verificar `must_change_password=false`.
5. Chamar `GET /auth/me` com token novo e confirmar identidade.
6. Forcar 5 logins invalidos consecutivos e confirmar resposta `401` neutra.
7. Simular indisponibilidade de dependencia e confirmar `503` com header `Retry-After`.

## Checkpoints de qualidade

- `mypy` sem erros em `backend/src`
- `pytest` verde para suites unit, contract e integration
- lockout nao vaza estado da conta na mensagem HTTP
- `openapi.yaml` alinhado com codigos 200/400/401/409/503 e `Retry-After`
- frontend exibe mensagens neutras para 401 e orientacao de retry para 503

## Troubleshooting rapido

- Erro de import no backend:
  - confirme `PYTHONPATH=src` ao executar `uvicorn` e `pytest`.
- Falha de conexao no PostgreSQL:
  - valide `DATABASE_URL` e permissao de acesso ao banco.
- 503 no login durante testes locais:
  - verifique se a API consegue abrir conexao no banco.
- Token invalido em `/auth/me`:
  - valide `JWT_SECRET_KEY`, `JWT_ISSUER` e `JWT_AUDIENCE` coerentes entre emissao e validacao.
