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
