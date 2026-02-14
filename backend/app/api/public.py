from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import Optional
import logging

from app.db.session import get_db
from app.models.user import Site, Geofence, IPRule, AccessAudit
from app.services.access_control import access_control_service
from app.services.screenshot import screenshot_service
from app.services.ip_rules import IPRuleData
from app.services.content import content_service

router = APIRouter(tags=["public:site"])
logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def parse_client_gps(request: Request) -> tuple[Optional[float], Optional[float]]:
    """Parse client GPS from header."""
    gps_header = request.headers.get("X-Client-GPS")
    if not gps_header:
        return None, None
    
    try:
        parts = gps_header.split(",")
        if len(parts) == 2:
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            return lat, lon
    except ValueError:
        pass
    
    return None, None


async def get_site_by_identifier(
    site_id: str,
    db: AsyncSession
) -> Optional[Site]:
    """Get site by ID or hostname."""
    try:
        uuid_id = UUID(site_id)
        result = await db.execute(
            select(Site).where(Site.id == uuid_id)
        )
    except ValueError:
        # Not a UUID, try hostname
        result = await db.execute(
            select(Site).where(Site.hostname == site_id)
        )
    
    return result.scalar_one_or_none()


async def get_site_config(
    site_id: UUID,
    db: AsyncSession
) -> tuple[list[dict], list[IPRuleData]]:
    """Get geofences and IP rules for a site."""
    # Get all geofences
    result = await db.execute(
        select(Geofence).where(
            Geofence.site_id == site_id,
            Geofence.is_active == True
        )
    )
    geofences = result.scalars().all()
    
    geofences_data = []
    for geofence in geofences:
        geofences_data.append({
            "polygon": geofence.polygon,
            "center_lat": geofence.center_lat,
            "center_lon": geofence.center_lon,
            "radius_meters": geofence.radius_meters,
        })
    
    # Get IP rules
    result = await db.execute(
        select(IPRule).where(
            IPRule.site_id == site_id,
            IPRule.is_active == True
        ).order_by(IPRule.priority)
    )
    ip_rules = result.scalars().all()
    
    ip_rules_data = [
        IPRuleData(cidr=r.cidr, action=r.action)
        for r in ip_rules
    ]
    
    return geofences_data, ip_rules_data


async def create_audit_entry(
    site_id: UUID,
    client_ip: str,
    decision: str,
    reason: str,
    ip_geo: Optional[dict],
    client_gps_lat: Optional[float],
    client_gps_lon: Optional[float],
    user_agent: Optional[str],
    artifact_s3_key: Optional[str],
    db: AsyncSession
):
    """Create an audit log entry."""
    audit = AccessAudit(
        site_id=site_id,
        client_ip=client_ip,
        ip_geo_country=ip_geo.get("country") if ip_geo else None,
        ip_geo_city=ip_geo.get("city") if ip_geo else None,
        ip_geo_lat=str(ip_geo.get("lat")) if ip_geo and ip_geo.get("lat") else None,
        ip_geo_lon=str(ip_geo.get("lon")) if ip_geo and ip_geo.get("lon") else None,
        client_gps_lat=str(client_gps_lat) if client_gps_lat else None,
        client_gps_lon=str(client_gps_lon) if client_gps_lon else None,
        decision=decision,
        reason=reason,
        user_agent=user_agent,
        artifact_s3_key=artifact_s3_key,
    )
    db.add(audit)
    await db.commit()


@router.api_route("/s/{site_id}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def site_access(
    site_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle site access with geo/IP filtering."""
    # Get site
    site = await get_site_by_identifier(site_id, db)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found"
        )
    
    # Get client info
    client_ip = get_client_ip(request)
    client_gps_lat, client_gps_lon = parse_client_gps(request)
    user_agent = request.headers.get("User-Agent")
    
    # Get site config
    geofences_data, ip_rules = await get_site_config(site.id, db)
    
    # Evaluate access
    decision = await access_control_service.evaluate_access(
        filter_mode=site.filter_mode.value if hasattr(site.filter_mode, 'value') else str(site.filter_mode),
        client_ip=client_ip,
        client_gps_lat=client_gps_lat,
        client_gps_lon=client_gps_lon,
        ip_rules=ip_rules,
        geofences_data=geofences_data,
    )
    
    # Create audit entry
    artifact_s3_key = None
    if not decision.allowed:
        # Try to capture screenshot
        try:
            block_page_url = str(request.url)
            artifact_s3_key = await screenshot_service.capture_block_page(
                str(site.id),
                client_ip,
                decision.reason,
                block_page_url
            )
        except Exception:
            logger.exception("screenshot capture failed", extra={"site_id": str(site.id)})
    
    await create_audit_entry(
        site_id=site.id,
        client_ip=client_ip,
        decision="allowed" if decision.allowed else "blocked",
        reason=decision.reason,
        ip_geo=decision.ip_geo,
        client_gps_lat=client_gps_lat,
        client_gps_lon=client_gps_lon,
        user_agent=user_agent,
        artifact_s3_key=artifact_s3_key,
        db=db,
    )
    
    if not decision.allowed:
        # Return block page
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{site.block_page_title}</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                        margin: 0;
                        background: #f5f5f5;
                    }}
                    .container {{
                        background: white;
                        padding: 2rem;
                        border-radius: 8px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        text-align: center;
                        max-width: 500px;
                    }}
                    h1 {{ color: #dc2626; }}
                    p {{ color: #6b7280; line-height: 1.6; }}
                    .reason {{ 
                        background: #fef2f2; 
                        padding: 1rem; 
                        border-radius: 4px; 
                        margin: 1rem 0;
                        font-size: 0.9rem;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>{site.block_page_title}</h1>
                    <div class="reason">Reason: {decision.reason}</div>
                    <p>{site.block_page_message}</p>
                    <p><small>If you believe this is an error, please contact the site administrator.</small></p>
                </div>
            </body>
            </html>
            """,
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    # Access allowed - return placeholder (in production, serve actual site content)
    return JSONResponse({
        "status": "ok",
        "message": "Access granted",
        "site": site.name,
    })


@router.get("/s/{site_id}/content/{filename:path}")
async def serve_site_content(
    site_id: str,
    filename: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Serve site content if access is allowed."""
    site = await get_site_by_identifier(site_id, db)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    client_ip = get_client_ip(request)
    client_gps_lat, client_gps_lon = parse_client_gps(request)
    user_agent = request.headers.get("User-Agent")
    
    geofences_data, ip_rules = await get_site_config(site.id, db)
    
    decision = await access_control_service.evaluate_access(
        filter_mode=site.filter_mode.value if hasattr(site.filter_mode, 'value') else str(site.filter_mode),
        client_ip=client_ip,
        client_gps_lat=client_gps_lat,
        client_gps_lon=client_gps_lon,
        ip_rules=ip_rules,
        geofences_data=geofences_data,
    )
    
    await create_audit_entry(
        site_id=site.id,
        client_ip=client_ip,
        decision="allowed" if decision.allowed else "blocked",
        reason=decision.reason,
        ip_geo=decision.ip_geo,
        client_gps_lat=client_gps_lat,
        client_gps_lon=client_gps_lon,
        user_agent=user_agent,
        artifact_s3_key=None,
        db=db,
    )
    
    if not decision.allowed:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        result = await content_service.get_file(site_id, filename)
        if not result:
            raise HTTPException(status_code=404, detail="File not found")
    except HTTPException:
        raise
    except Exception:
        logger.exception("content fetch failed", extra={"site_id": str(site.id), "filename": filename})
        raise HTTPException(status_code=503, detail="Content unavailable")
    
    file_data, content_type = result
    return Response(content=file_data, media_type=content_type)
