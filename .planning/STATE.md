# Current State

## Repository Summary

- Backend: FastAPI app with async SQLAlchemy, JWT auth, access control, and audit logging.
- Frontend: React + Vite admin UI with pages for sites, users, audit logs, and content.
- Storage: PostgreSQL + PostGIS intended, Redis caching, MinIO/S3 for artifacts.
- Tests: pytest unit tests and Playwright e2e test exist.

## Observed Implementation Notes

- Config uses dev defaults (DEBUG true, dev secret key, permissive CORS).
- Database schema uses SQLAlchemy models with create_all but no migrations.
- IP geo lookup is placeholder and Redis cache is optional.
- Screenshot capture relies on Playwright and uploads to S3.
- Public access endpoint returns JSON placeholder instead of actual site content.
- Access audit logs are written on every request.

## Known Gaps

- No migration tooling or schema versioning in repo.
- No production-safe config defaults and no secrets management guidance.
- No explicit readiness/liveness checks beyond a simple /health.
- No structured logging or request correlation.
- No rate limiting or abuse protection.
- Limited automated test coverage of public access and admin APIs.
- Content delivery path is basic and not optimized for scale.
- Background processing is not present for screenshots or uploads.

## Planning Assumptions

- This roadmap targets a baseline production deployment for the current feature set.
- No additional features beyond known gaps are in scope.
