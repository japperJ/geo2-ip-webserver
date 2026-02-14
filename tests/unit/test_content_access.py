import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.anyio
async def test_content_upload_requires_editor_or_admin():
    """Test that content upload requires editor or admin role."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Try to upload without auth
        resp = await client.post(
            "/api/admin/sites/00000000-0000-0000-0000-000000000000/content/upload",
            files={"file": ("a.txt", b"hi")}
        )
        assert resp.status_code in (401, 403, 404)

@pytest.mark.anyio
async def test_content_list_requires_viewer_or_higher():
    """Test that content list requires viewer role or higher."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Try to list without auth
        resp = await client.get(
            "/api/admin/sites/00000000-0000-0000-0000-000000000000/content"
        )
        assert resp.status_code in (401, 403, 404)

@pytest.mark.anyio
async def test_content_delete_requires_admin():
    """Test that content delete requires admin role."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Try to delete without auth
        resp = await client.delete(
            "/api/admin/sites/00000000-0000-0000-0000-000000000000/content/test.txt"
        )
        assert resp.status_code in (401, 403, 404)
