import logging
from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)


class AuditLogService:
    async def log_public_access(
        self,
        db: AsyncSession,
        site_id: UUID,
        client_ip: str,
        allowed: bool,
        reason: str,
        ip_geo: Optional[dict] = None,
        client_gps_lat: Optional[float] = None,
        client_gps_lon: Optional[float] = None,
        user_agent: Optional[str] = None,
        artifact_s3_key: Optional[str] = None,
    ):
        """Create an audit log entry for public access."""
        from app.models.user import AccessAudit
        
        audit = AccessAudit(
            site_id=site_id,
            client_ip=client_ip,
            ip_geo_country=ip_geo.get("country") if ip_geo else None,
            ip_geo_city=ip_geo.get("city") if ip_geo else None,
            ip_geo_lat=str(ip_geo.get("lat")) if ip_geo and ip_geo.get("lat") else None,
            ip_geo_lon=str(ip_geo.get("lon")) if ip_geo and ip_geo.get("lon") else None,
            client_gps_lat=str(client_gps_lat) if client_gps_lat else None,
            client_gps_lon=str(client_gps_lon) if client_gps_lon else None,
            decision="allowed" if allowed else "blocked",
            reason=reason,
            user_agent=user_agent,
            artifact_s3_key=artifact_s3_key,
        )
        db.add(audit)
        await db.commit()
        await db.refresh(audit)
        return audit

    async def list_entries(
        self,
        db: AsyncSession,
        site_id: Optional[UUID] = None,
        limit: int = 100,
        offset: int = 0,
    ):
        """List audit log entries."""
        from app.models.user import AccessAudit
        
        query = select(AccessAudit)
        
        if site_id:
            query = query.where(AccessAudit.site_id == site_id)
        
        query = query.order_by(AccessAudit.timestamp.desc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        return result.scalars().all()


audit_log_service = AuditLogService()
