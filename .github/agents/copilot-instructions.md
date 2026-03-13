# oficina_sdd_v04 Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-13

## Active Technologies
- PostgreSQL 16+ accessed exclusively through psycopg 3 with explicit SQL and no ORM (001-login-admin)
- Python 3.12 and TypeScript 5.x + FastAPI, Uvicorn, psycopg 3, psycopg_pool, PyJWT, argon2-cffi, Pydantic v2, pydantic-settings, ReactJS, Vite, React Router, Axios (001-login-admin)
- Python 3.12 and TypeScript 5.x + FastAPI, Uvicorn, psycopg 3, psycopg_pool, PyJWT, argon2-cffi, Pydantic v2, pydantic-settings, React, Vite, React Router, Axios (001-login-admin)
- PostgreSQL 16+ via psycopg 3 with explicit SQL (no ORM) (001-login-admin)

## Project Structure

```text
backend/
frontend/
sql/
```

## Commands

- `cd backend && pytest tests/unit`
- `cd backend && pytest tests/contract`
- `cd backend && pytest tests/integration`
- `cd frontend && npm run test -- --run`
- `cd frontend && npm run build`

## Code Style

Python 3.12: use Object-Oriented Design, Hexagonal Architecture, Repository
pattern, strict typing, explicit SQL with psycopg 3, and TDD-first delivery.
TypeScript/React: strict TypeScript, typed API contracts, component
composition, and tests with Vitest + React Testing Library.

## Recent Changes
- 001-login-admin: Added Python 3.12 and TypeScript 5.x + FastAPI, Uvicorn, psycopg 3, psycopg_pool, PyJWT, argon2-cffi, Pydantic v2, pydantic-settings, React, Vite, React Router, Axios
- 001-login-admin: Added Python 3.12 and TypeScript 5.x + FastAPI, Uvicorn, psycopg 3, psycopg_pool, PyJWT, argon2-cffi, Pydantic v2, pydantic-settings, ReactJS, Vite, React Router, Axios

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
