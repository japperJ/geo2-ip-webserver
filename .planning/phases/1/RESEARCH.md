# Phase 1 Research: MVP Stabilization

## Summary
Research focused on Phase 1 goals in `.planning/ROADMAP.md` and existing repo configuration for backend, frontend, and local infrastructure. The stack appears to be FastAPI + PostgreSQL + Redis + MinIO with a Vite/React frontend, and Docker Compose is already configured. There is no `.planning/research/SUMMARY.md`, so stack decisions are inferred from repo files. Confidence is MEDIUM for repo-derived details and LOW for anything that would normally require external verification.

## Standard Stack
| Need | Solution | Version | Confidence | Source |
|---|---|---|---|---|
| Backend API framework | FastAPI | >=0.109.0 | MEDIUM | `backend/requirements.txt` |
| ASGI server | Uvicorn | >=0.27.0 | MEDIUM | `backend/requirements.txt` |
| ORM / DB layer | SQLAlchemy | >=2.0.25 | MEDIUM | `backend/requirements.txt` |
| Postgres driver (async) | asyncpg | >=0.29.0 | MEDIUM | `backend/requirements.txt` |
| Auth/JWT | python-jose | >=3.3.0 | MEDIUM | `backend/requirements.txt` |
| Password hashing | passlib[bcrypt] | >=1.7.4 | MEDIUM | `backend/requirements.txt` |
| Cache/queue | Redis | 7-alpine (Docker) | MEDIUM | `docker-compose.yml` |
| Object storage | MinIO | latest (Docker) | MEDIUM | `docker-compose.yml` |
| Database | Postgres + PostGIS | 15-3.3 (Docker) | MEDIUM | `docker-compose.yml` |
| Frontend | React + Vite | React ^18.2, Vite ^5.0 | MEDIUM | `frontend/package.json` |
| HTTP client | Axios | ^1.6.5 | MEDIUM | `frontend/package.json` |
| Maps | Leaflet + React-Leaflet | ^1.9.4 / ^4.2.1 | MEDIUM | `frontend/package.json` |
| API tests | Playwright | >=1.41.0 | MEDIUM | `backend/requirements.txt`, `playwright.config.ts` |

## Architecture Patterns
### Pattern: Docker Compose local stack
Compose already defines Postgres, Redis, MinIO, backend, and frontend with health checks and a basic volume layout. Phase 1 should stabilize a single-command local startup path by aligning compose, backend run instructions, and frontend dev/build steps.

### Pattern: FastAPI service with async DB
The dependency set indicates an async-first FastAPI service using SQLAlchemy 2.x + asyncpg. Ensure any auth, access control, and audit logging additions are async-compatible and do not block request handling.

## Don't Hand-Roll
| Feature | Use Instead | Why |
|---|---|---|
| Password hashing | passlib[bcrypt] | Already listed; keep hashing consistent and avoid custom crypto. |
| JWT encode/decode | python-jose | Already listed; avoid custom token logic. |
| DB migrations (Phase 2) | alembic | Already included; do not invent custom migration system. |

## Common Pitfalls
1. **Inconsistent auth error codes** — Ensure all auth endpoints return consistent status codes and error shapes for invalid credentials, expired tokens, and missing auth.
2. **Async + blocking I/O** — Screenshot capture and storage calls can block the event loop; ensure failures are handled and do not crash requests.
3. **Non-deterministic access control** — If multiple rules apply, define deterministic precedence for allow/block and ensure it is logged.
4. **Audit logging gaps** — Public access requests must always write audit entries, even on deny or downstream errors.

## Code Examples
Not included. Verified examples require inspecting backend route and auth implementation files and possibly external references.

## Open Questions
1. Where are auth routes, access control decision logic, and audit logging implemented in the backend?
2. What is the expected error response schema for auth and public access endpoints?
3. How are screenshot capture and content uploads currently wired (sync vs async)?
4. Which endpoints are public vs role-protected and what are the current role names?
5. Is Playwright intended for API tests, e2e UI tests, or both?

## Sources
| Source | Type | Confidence |
|---|---|---|
| `.planning/ROADMAP.md` | local | HIGH |
| `.planning/REQUIREMENTS.md` | local | HIGH |
| `backend/requirements.txt` | local | MEDIUM |
| `pyproject.toml` | local | MEDIUM |
| `docker-compose.yml` | local | MEDIUM |
| `backend/Dockerfile` | local | MEDIUM |
| `frontend/Dockerfile` | local | MEDIUM |
| `frontend/package.json` | local | MEDIUM |
