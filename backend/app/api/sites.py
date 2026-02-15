from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User, Site, SiteUser
from app.schemas import (
    SiteCreate,
    SiteUpdate,
    SiteResponse,
    FilterConfig,
)
from app.services.ip_rules import IPRuleData
from app.services.access_control import access_control_service
from app.services.screenshot import screenshot_service

router = APIRouter(prefix="/admin/sites", tags=["admin:sites"])


async def get_site_with_access(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> tuple[Site, str]:
    """Get site and verify user has access. Returns (site, role)."""
    result = await db.execute(
        select(Site).where(Site.id == site_id)
    )
    site = result.scalar_one_or_none()
    
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found"
        )
    
    role = None
    
    # Check if user is super admin
    if current_user.is_admin:
        role = "admin"
    # Check if user is owner
    elif site.owner_user_id == current_user.id:
        role = "owner"
    else:
        # Check site_users for role
        result = await db.execute(
            select(SiteUser).where(
                SiteUser.site_id == site_id,
                SiteUser.user_id == current_user.id
            )
        )
        site_user = result.scalar_one_or_none()
        if site_user:
            role = site_user.role.value if hasattr(site_user.role, 'value') else site_user.role
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this site"
        )
    
    return site, role


async def get_site_for_write(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Site:
    """Get site and verify user has admin access for write operations."""
    site, role = await get_site_with_access(site_id, db, current_user)
    if role not in ['owner', 'admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this site"
        )
    return site


@router.get("", response_model=list[SiteResponse])
async def list_sites(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all sites the user has access to."""
    if current_user.is_admin:
        # Super admins see all sites
        result = await db.execute(select(Site))
    else:
        # Regular users see sites they own or are members of (any role)
        result = await db.execute(
            select(Site).where(
                (Site.owner_user_id == current_user.id) |
                (Site.id.in_(
                    select(SiteUser.site_id).where(
                        SiteUser.user_id == current_user.id
                    )
                ))
            )
        )
    
    return result.scalars().all()


@router.post("", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site(
    site_data: SiteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new site."""
    site = Site(
        name=site_data.name,
        hostname=site_data.hostname,
        path_prefix=site_data.path_prefix,
        owner_user_id=current_user.id,
        filter_mode=site_data.filter_mode,
    )
    db.add(site)
    await db.commit()
    await db.refresh(site)
    return site


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific site."""
    site, role = await get_site_with_access(site_id, db, current_user)
    site.my_role = role
    return site


@router.put("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_data: SiteUpdate,
    site: Site = Depends(get_site_for_write),
    db: AsyncSession = Depends(get_db)
):
    """Update a site."""
    if site_data.name is not None:
        site.name = site_data.name
    if site_data.hostname is not None:
        site.hostname = site_data.hostname
    if site_data.path_prefix is not None:
        site.path_prefix = site_data.path_prefix
    if site_data.filter_mode is not None:
        site.filter_mode = site_data.filter_mode
    if site_data.block_page_title is not None:
        site.block_page_title = site_data.block_page_title
    if site_data.block_page_message is not None:
        site.block_page_message = site_data.block_page_message
    
    await db.commit()
    await db.refresh(site)
    return site


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site(
    site: Site = Depends(get_site_for_write),
    db: AsyncSession = Depends(get_db)
):
    """Delete a site."""
    await db.delete(site)
    await db.commit()


@router.put("/{site_id}/filter", response_model=SiteResponse)
async def update_filter_config(
    filter_config: FilterConfig,
    site: Site = Depends(get_site_for_write),
    db: AsyncSession = Depends(get_db)
):
    """Update filter configuration for a site."""
    site.filter_mode = filter_config.filter_mode
    
    # Update geofence if provided
    if filter_config.geofence:
        from app.models.user import Geofence
        
        # Delete existing geofences
        result = await db.execute(
            select(Geofence).where(Geofence.site_id == site.id)
        )
        existing = result.scalars().all()
        for g in existing:
            await db.delete(g)
        
        # Create new geofence
        geofence = Geofence(
            site_id=site.id,
            name=filter_config.geofence.name,
            polygon=filter_config.geofence.polygon,
            center_lat=str(filter_config.geofence.center_lat) if filter_config.geofence.center_lat else None,
            center_lon=str(filter_config.geofence.center_lon) if filter_config.geofence.center_lon else None,
            radius_meters=str(filter_config.geofence.radius_meters) if filter_config.geofence.radius_meters else None,
        )
        db.add(geofence)
    
    # Update IP rules if provided
    if filter_config.ip_rules:
        from app.models.user import IPRule
        
        # Delete existing IP rules
        result = await db.execute(
            select(IPRule).where(IPRule.site_id == site.id)
        )
        existing = result.scalars().all()
        for r in existing:
            await db.delete(r)
        
        # Create new IP rules
        for rule_data in filter_config.ip_rules:
            rule = IPRule(
                site_id=site.id,
                cidr=rule_data.cidr,
                action=rule_data.action,
                description=rule_data.description,
                priority=str(rule_data.priority) if rule_data.priority else "0",
            )
            db.add(rule)
    
    await db.commit()
    await db.refresh(site)
    return site
