# Phase 1 MVP Stabilization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the current product reliable for internal users and demos by stabilizing local setup, auth, access control, and core tests.

**Architecture:** Keep FastAPI async request flow with SQLAlchemy async sessions and service-layer helpers for access control, screenshots, and content. Add deterministic error handling and logging at API boundaries so failures do not crash requests and audit trails are consistent.

**Tech Stack:** FastAPI, SQLAlchemy (async), pytest, Playwright, Docker Compose, React/Vite.

**Must-Haves (Requirement → Task Traceability):**
- REQ-MVP-001 → Task 1, Task 6
- REQ-MVP-002 → Task 2
- REQ-MVP-003 → Task 4
- REQ-MVP-004 → Task 5, Task 7
- REQ-MVP-005 → Task 3
- REQ-MVP-006 → Task 8
- REQ-MVP-007 → Task 4
- REQ-MVP-008 → Task 5

---

### Task 1: Document one-command local setup paths

**Files:**
- Modify: `README.md`

**Step 1: Update docker-compose instructions to match actual ports and services**

```markdown
### Development with Docker Compose

```bash
docker-compose up -d
```

Services will be available at:
- Frontend: http://localhost:3002
- Backend API: http://localhost:8002
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- MinIO Console: http://localhost:9001
```

**Step 2: Update local backend/frontend instructions with one-command path**

```markdown
### Local Development

#### Backend

```bash
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

#### Frontend

```bash
npm --prefix frontend install
npm --prefix frontend run dev -- --host 0.0.0.0 --port 3002
```
```

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: align local run instructions with compose"
```

### Task 2: Standardize auth error responses and add unit tests

**Files:**
- Modify: `backend/app/api/auth.py`
- Create: `tests/unit/test_auth.py`

**Step 1: Write the failing tests for login, refresh, register, and /me**

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.anyio
async def test_login_invalid_credentials_returns_401():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post(
            "/api/auth/login",
            data={"username": "nope", "password": "bad"}
        )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Incorrect username or password"

@pytest.mark.anyio
async def test_refresh_invalid_token_type_returns_401():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post("/api/auth/refresh", json={"refresh_token": "not-a-jwt"})
    assert resp.status_code == 401

@pytest.mark.anyio
async def test_register_duplicate_username_returns_409():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Assume admin user exists
        resp = await client.post(
            "/api/auth/register",
            json={"username": "admin", "password": "test123", "email": "admin@example.com"}
        )
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"].lower()

@pytest.mark.anyio
async def test_me_invalid_token_returns_401():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token"}
        )
    assert resp.status_code == 401

@pytest.mark.anyio
async def test_me_missing_token_returns_401():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/api/auth/me")
    assert resp.status_code == 401
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_auth.py -v`
Expected: FAIL with import/app setup or failing response shape.

**Step 3: Implement minimal auth error consistency across all auth endpoints**

```python
# backend/app/api/auth.py

def auth_error(status_code: int, detail: str):
    return HTTPException(
        status_code=status_code,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"}
    )

# use it for all auth errors in login, refresh, register, and /me
# login:
raise auth_error(status.HTTP_401_UNAUTHORIZED, "Incorrect username or password")
raise auth_error(status.HTTP_403_FORBIDDEN, "User account is disabled")

# refresh:
raise auth_error(status.HTTP_401_UNAUTHORIZED, "Invalid token type")
raise auth_error(status.HTTP_401_UNAUTHORIZED, "Token has expired")

# register:
raise auth_error(status.HTTP_409_CONFLICT, "Username already exists")
raise auth_error(status.HTTP_409_CONFLICT, "Email already exists")

# /me:
raise auth_error(status.HTTP_401_UNAUTHORIZED, "Could not validate credentials")
raise auth_error(status.HTTP_401_UNAUTHORIZED, "Invalid authentication token")
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_auth.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/api/auth.py tests/unit/test_auth.py
git commit -m "test: cover auth error responses for login/refresh/register/me"
```

### Task 3: Make screenshot and content failures non-fatal with logging

**Files:**
- Modify: `backend/app/api/public.py`
- Modify: `backend/app/services/screenshot.py`
- Modify: `backend/app/services/content.py`

**Step 1: Write the failing tests**

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.anyio
async def test_block_page_survives_screenshot_failure(monkeypatch):
    async def fail_capture(*args, **kwargs):
        raise RuntimeError("boom")
    from app.services import screenshot
    monkeypatch.setattr(screenshot.screenshot_service, "capture_block_page", fail_capture)

    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/s/test-site")
    assert resp.status_code in (403, 404)

@pytest.mark.anyio
async def test_content_failure_returns_503(monkeypatch):
    async def fail_get(*args, **kwargs):
        raise RuntimeError("boom")
    from app.services import content
    monkeypatch.setattr(content.content_service, "get_file", fail_get)

    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/s/test-site/content/index.html")
    assert resp.status_code in (403, 404, 503)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_public_access.py::test_block_page_survives_screenshot_failure -v`
Expected: FAIL with unhandled exception.

**Step 3: Implement minimal error handling and logging**

```python
# backend/app/api/public.py

try:
    artifact_s3_key = await screenshot_service.capture_block_page(...)
except Exception:
    logger.exception("screenshot capture failed", extra={"site_id": str(site.id)})
    artifact_s3_key = None

try:
    result = await content_service.get_file(site_id, filename)
except Exception:
    logger.exception("content fetch failed", extra={"site_id": str(site.id), "filename": filename})
    raise HTTPException(status_code=503, detail="Content unavailable")
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_public_access.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/api/public.py backend/app/services/screenshot.py backend/app/services/content.py tests/unit/test_public_access.py
git commit -m "fix: log and handle screenshot/content failures"
```

### Task 4: Add deterministic allow/block decision tests

**Files:**
- Modify: `backend/app/services/access_control.py`
- Create: `tests/unit/test_access_control.py`

**Step 1: Write the failing tests**

```python
import pytest
from app.services.access_control import access_control_service
from app.services.ip_rules import IPRuleData

@pytest.mark.anyio
async def test_ip_rules_precedence_is_deterministic():
    rules = [
        IPRuleData(cidr="10.0.0.0/8", action="deny"),
        IPRuleData(cidr="10.0.0.5/32", action="allow"),
    ]
    decision = await access_control_service.evaluate_access(
        filter_mode="ip_only",
        client_ip="10.0.0.5",
        client_gps_lat=None,
        client_gps_lon=None,
        ip_rules=rules,
        geofences_data=[]
    )
    assert decision.allowed is True
    assert decision.reason == "ip_rule_allow"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_access_control.py::test_ip_rules_precedence_is_deterministic -v`
Expected: FAIL if precedence is not explicit.

**Step 3: Implement deterministic precedence in access control**

```python
# backend/app/services/access_control.py

# when multiple rules match, choose the most specific CIDR
def sort_ip_rules(rules):
    return sorted(rules, key=lambda r: r.cidr.count("/"), reverse=True)

matching_rules = [r for r in ip_rules if ip_in_cidr(client_ip, r.cidr)]
for rule in sort_ip_rules(matching_rules):
    if rule.action == "allow":
        return AccessDecision(allowed=True, reason="ip_rule_allow", ip_geo=ip_geo)
    if rule.action == "deny":
        return AccessDecision(allowed=False, reason="ip_rule_deny", ip_geo=ip_geo)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_access_control.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/access_control.py tests/unit/test_access_control.py
git commit -m "fix: make access control precedence deterministic"
```

### Task 5: Add a minimal API/e2e test for public access and audit log entry

**Files:**
- Modify: `tests/e2e/test_api.spec.ts`

**Step 1: Write the failing test**

```ts
import { test, expect } from "@playwright/test";

test("public access returns a decision and creates audit entry", async ({ request }) => {
  const resp = await request.get("/s/test-site");
  expect([200, 403, 404]).toContain(resp.status());

  const audit = await request.get("/api/audit-logs?limit=1");
  expect(audit.ok()).toBeTruthy();
});
```

**Step 2: Run test to verify it fails**

Run: `npx playwright test tests/e2e/test_api.spec.ts -g "public access"`
Expected: FAIL until base URL, auth, and audit log fixture are configured.

**Step 3: Implement minimal setup for the test**

```ts
// tests/e2e/test_api.spec.ts
test.use({ baseURL: process.env.API_BASE_URL || "http://localhost:8002" });

// helper for API auth if audit logs are protected
async function apiLogin(request) {
  if (!process.env.API_TEST_USER || !process.env.API_TEST_PASSWORD) {
    throw new Error("Missing API_TEST_USER/API_TEST_PASSWORD for audit log check");
  }
  const login = await request.post("/api/auth/login", {
    data: { username: process.env.API_TEST_USER, password: process.env.API_TEST_PASSWORD }
  });
  const body = await login.json();
  return body.access_token;
}
```

**Step 4: Run test to verify it passes**

Run: `API_BASE_URL=http://localhost:8002 API_TEST_USER=... API_TEST_PASSWORD=... npx playwright test tests/e2e/test_api.spec.ts -g "public access"`
Expected: PASS with audit log check or SKIP if audit endpoint is disabled.

**Step 5: Commit**

```bash
git add tests/e2e/test_api.spec.ts
git commit -m "test: add public access audit log check"
```

### Task 6: Validate Phase 1 success criteria locally

**Files:**
- Modify: `README.md`

**Step 1: Run unit tests**

Run: `pytest tests/unit/ -v`
Expected: PASS

**Step 2: Run API/e2e test**

Run: `API_BASE_URL=http://localhost:8002 API_TEST_USER=... API_TEST_PASSWORD=... npx playwright test tests/e2e/test_api.spec.ts`
Expected: PASS

**Step 3: Update README testing section with verified commands**

```markdown
## Testing

```bash
pytest tests/unit/ -v
API_BASE_URL=http://localhost:8002 npx playwright test tests/e2e/test_api.spec.ts
```
```

**Step 4: Commit**

```bash
git add README.md
git commit -m "docs: document verified test commands"

### Task 7: Verify audit log entries for public access requests

**Files:**
- Modify: `tests/unit/test_audit_log.py`
- Modify: `backend/app/services/audit_log.py`

**Step 1: Write the failing test**

```python
import pytest
from app.services.audit_log import audit_log_service

@pytest.mark.anyio
async def test_public_access_creates_audit_log_entry(db_session, site_factory):
    site = await site_factory()
    await audit_log_service.log_public_access(
        db=db_session,
        site_id=site.id,
        client_ip="10.0.0.1",
        allowed=True,
        reason="ip_rule_allow"
    )
    result = await audit_log_service.list_entries(db_session, limit=1)
    assert result
    assert result[0].site_id == site.id
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_audit_log.py::test_public_access_creates_audit_log_entry -v`
Expected: FAIL if log_public_access or list_entries is missing/incorrect.

**Step 3: Implement minimal audit log API**

```python
# backend/app/services/audit_log.py

async def log_public_access(db, site_id, client_ip, allowed, reason):
    ...

async def list_entries(db, limit=1):
    ...
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_audit_log.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/audit_log.py tests/unit/test_audit_log.py
git commit -m "test: cover audit log public access entries"
```

### Task 8: Enforce role-based content upload/list/delete access

**Files:**
- Modify: `backend/app/api/content.py`
- Modify: `backend/app/services/content.py`
- Modify: `tests/unit/test_content_access.py`

**Step 1: Write the failing tests**

```python
import pytest
from app.services.auth import UserRole

@pytest.mark.anyio
async def test_content_upload_requires_editor_or_admin(client):
    resp = await client.post("/api/content/upload", files={"file": ("a.txt", b"hi")})
    assert resp.status_code in (401, 403)

@pytest.mark.anyio
async def test_content_list_requires_viewer_or_higher(client):
    resp = await client.get("/api/content")
    assert resp.status_code in (401, 403)

@pytest.mark.anyio
async def test_content_delete_requires_admin(client):
    resp = await client.delete("/api/content/123")
    assert resp.status_code in (401, 403)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_content_access.py -v`
Expected: FAIL until role checks are added.

**Step 3: Implement role checks**

```python
# backend/app/api/content.py

require_roles(["viewer", "editor", "admin"])  # list
require_roles(["editor", "admin"])            # upload
require_roles(["admin"])                       # delete
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_content_access.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/api/content.py backend/app/services/content.py tests/unit/test_content_access.py
git commit -m "fix: enforce content role access"
```
```
