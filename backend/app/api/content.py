from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List
import logging

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User, Site, SiteUser, SiteUserRole
from app.services.content import content_service, ContentFile
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/sites/{site_id}/content", tags=["admin:content"])


class ContentFileResponse(BaseModel):
    key: str
    filename: str
    content_type: str
    size: int
    uploaded_at: str


async def verify_site_admin(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Site:
    """Verify user has admin access to site (for delete operations)."""
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()
    
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    if current_user.is_admin:
        return site
    
    if site.owner_user_id == current_user.id:
        return site
    
    result = await db.execute(
        select(SiteUser).where(
            SiteUser.site_id == site_id,
            SiteUser.user_id == current_user.id,
            SiteUser.role == SiteUserRole.ADMIN
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return site


async def verify_site_editor(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Site:
    """Verify user has editor access to site (for upload operations)."""
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()
    
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    if current_user.is_admin:
        return site
    
    if site.owner_user_id == current_user.id:
        return site
    
    result = await db.execute(
        select(SiteUser).where(
            SiteUser.site_id == site_id,
            SiteUser.user_id == current_user.id,
            SiteUser.role.in_([SiteUserRole.ADMIN, SiteUserRole.EDITOR])
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Editor access required")
    
    return site


async def verify_site_viewer(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Site:
    """Verify user has viewer access to site (for list operations)."""
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()
    
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    if current_user.is_admin:
        return site
    
    if site.owner_user_id == current_user.id:
        return site
    
    result = await db.execute(
        select(SiteUser).where(
            SiteUser.site_id == site_id,
            SiteUser.user_id == current_user.id,
            SiteUser.role.in_([SiteUserRole.ADMIN, SiteUserRole.EDITOR, SiteUserRole.VIEWER])
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Viewer access required")
    
    return site


@router.get("", response_model=List[ContentFileResponse])
async def list_content(
    site: Site = Depends(verify_site_viewer),
):
    """List all content files for a site (requires viewer role or higher)."""
    files = await content_service.list_files(str(site.id))
    return [
        ContentFileResponse(
            key=f.key,
            filename=f.filename,
            content_type=f.content_type,
            size=f.size,
            uploaded_at=f.uploaded_at.isoformat() if hasattr(f.uploaded_at, 'isoformat') else str(f.uploaded_at)
        )
        for f in files
    ]


@router.post("/upload", response_model=ContentFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_content(
    file: UploadFile = File(...),
    site: Site = Depends(verify_site_editor),
):
    """Upload a content file to a site (requires editor role or higher)."""
    file_data = await file.read()
    
    content_file = await content_service.upload_file(
        site_id=str(site.id),
        file_data=file_data,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream"
    )
    
    return ContentFileResponse(
        key=content_file.key,
        filename=content_file.filename,
        content_type=content_file.content_type,
        size=content_file.size,
        uploaded_at=content_file.uploaded_at.isoformat()
    )


@router.delete("/{key:path}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_content(
    key: str,
    site: Site = Depends(verify_site_admin),
):
    """Delete a content file (requires admin role)."""
    success = await content_service.delete_file(str(site.id), key)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete file")
