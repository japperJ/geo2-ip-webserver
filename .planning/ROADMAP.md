# Roadmap

Mode: Roadmap. Phases are ordered and cumulative.

## Phase 1: MVP Stabilization

Goal: Make the current product reliable for internal users and demos.

Scope:
- Document how to run backend + frontend locally and via docker-compose.
- Stabilize auth flows and role-based access control behavior.
- Ensure site access flow handles block/allow consistently and safely.
- Ensure audit logging, screenshots, and content storage have clear failure behavior.
- Add basic test coverage for core access control and public endpoints.

Success criteria:
- Local dev setup works from a clean clone with one command path per service.
- Auth/login/refresh endpoints behave consistently and return expected error codes.
- Public site access returns deterministic allow/block responses with audit entries.
- Screenshot and content upload failures do not crash requests and are logged.
- Core unit tests and at least one API/e2e test pass locally.

## Phase 2: Production Readiness

Goal: Make the system safe, secure, and operable in production.

Scope:
- Replace dev defaults (secret key, debug mode, permissive CORS) with env-driven config.
- Add database migrations and formal schema management.
- Harden API validation, rate limiting, and error responses.
- Add structured logging, request IDs, and health/readiness checks.
- Provide deployment guidance for Docker and environment variables.

Success criteria:
- No hard-coded secrets or dev defaults in production config.
- Database schema changes are managed with migrations.
- Public and admin APIs enforce validation and rate limits.
- Logs are structured and correlate requests across services.
- Deployment docs cover required env vars and storage dependencies.

## Phase 3: Scale / Ops

Goal: Support growth with performance, reliability, and operational tooling.

Scope:
- Introduce caching strategy and metrics for access decisions.
- Add background processing for screenshots and heavy IO paths.
- Implement backups, retention policies, and audit log lifecycle management.
- Add monitoring, alerting, and basic SLOs.
- Optimize content delivery and access checks for higher throughput.

Success criteria:
- Access decision path meets target latency under load.
- Screenshot capture and content workflows are async and resilient.
- Backups and retention policies are automated and tested.
- Metrics and alerts exist for error rates, latency, and queue health.
- System can be scaled horizontally with documented procedures.
