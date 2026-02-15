from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User, Site, SiteUser, AccessAudit
from app.schemas import AccessAuditResponse, AccessAuditSearch
from app.services.screenshot import screenshot_service

router = APIRouter(prefix="/admin/sites/{site_id}/audit", tags=["admin:audit"])


async def verify_site_access(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Site:
    """Verify user has access to site audit logs."""
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()
    
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    if site.owner_user_id != current_user.id:
        result = await db.execute(
            select(SiteUser).where(
                SiteUser.site_id == site_id,
                SiteUser.user_id == current_user.id,
                SiteUser.role.in_(["owner", "admin", "viewer"])
            )
        )
        if not result.scalar_one_or_none() and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    return site


@router.get("", response_model=List[AccessAuditResponse])
async def search_audit_logs(
    site: Site = Depends(verify_site_access),
    db: AsyncSession = Depends(get_db),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    decision: Optional[str] = Query(None),
    client_ip: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
):
    """Search audit logs for a site."""
    query = select(AccessAudit).where(AccessAudit.site_id == site.id)
    
    if from_date:
        query = query.where(AccessAudit.timestamp >= from_date)
    if to_date:
        query = query.where(AccessAudit.timestamp <= to_date)
    if decision:
        query = query.where(AccessAudit.decision == decision)
    if client_ip:
        query = query.where(AccessAudit.client_ip.like(f"%{client_ip}%"))
    
    query = query.order_by(AccessAudit.timestamp.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/export")
async def export_audit_logs_csv(
    site: Site = Depends(verify_site_access),
    db: AsyncSession = Depends(get_db),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    decision: Optional[str] = Query(None),
):
    """Export audit logs as CSV."""
    query = select(AccessAudit).where(AccessAudit.site_id == site.id)
    
    if from_date:
        query = query.where(AccessAudit.timestamp >= from_date)
    if to_date:
        query = query.where(AccessAudit.timestamp <= to_date)
    if decision:
        query = query.where(AccessAudit.decision == decision)
    
    query = query.order_by(AccessAudit.timestamp.desc())
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Generate CSV
    import csv
    from io import StringIO
    from fastapi.responses import StreamingResponse
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "timestamp", "client_ip", "ip_geo_country", "ip_geo_city",
        "client_gps_lat", "client_gps_lon", "decision", "reason", "user_agent"
    ])
    
    for log in logs:
        writer.writerow([
            log.timestamp.isoformat() if log.timestamp else "",
            log.client_ip or "",
            log.ip_geo_country or "",
            log.ip_geo_city or "",
            log.client_gps_lat or "",
            log.client_gps_lon or "",
            log.decision or "",
            log.reason or "",
            log.user_agent or "",
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=audit_{site.id}.csv"}
    )


@router.get("/{log_id}/screenshot")
async def get_screenshot(
    log_id: UUID,
    site: Site = Depends(verify_site_access),
    db: AsyncSession = Depends(get_db)
):
    """Get screenshot artifact for an audit log entry."""
    result = await db.execute(
        select(AccessAudit).where(
            AccessAudit.id == log_id,
            AccessAudit.site_id == site.id
        )
    )
    audit = result.scalar_one_or_none()
    
    if not audit or not audit.artifact_s3_key:
        raise HTTPException(status_code=404, detail="Screenshot not found")
    
    screenshot_data = await screenshot_service.get_screenshot(audit.artifact_s3_key)
    
    if not screenshot_data:
        raise HTTPException(status_code=404, detail="Screenshot not available")
    
    from fastapi.responses import Response
    return Response(content=screenshot_data, media_type="image/png")
