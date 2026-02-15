from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User, Site, Geofence, SiteUser, SiteUserRole
from app.schemas import GeofenceCreate, GeofenceUpdate, GeofenceResponse

router = APIRouter(prefix="/admin/sites/{site_id}/geofences", tags=["admin:geofences"])


async def verify_site_member(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Site:
    """Verify user is a member of the site (any role can view)."""
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()
    
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    if current_user.is_admin or site.owner_user_id == current_user.id:
        return site
    
    result = await db.execute(
        select(SiteUser).where(
            SiteUser.site_id == site_id,
            SiteUser.user_id == current_user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return site


async def verify_site_admin(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Site:
    """Verify user has admin access to site (owner, admin, or super admin)."""
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()
    
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    if current_user.is_admin or site.owner_user_id == current_user.id:
        return site
    
    result = await db.execute(
        select(SiteUser).where(
            SiteUser.site_id == site_id,
            SiteUser.user_id == current_user.id,
            SiteUser.role.in_([SiteUserRole.OWNER, SiteUserRole.ADMIN])
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return site


@router.get("", response_model=List[GeofenceResponse])
async def list_geofences(
    site: Site = Depends(verify_site_member),
    db: AsyncSession = Depends(get_db)
):
    """List all geofences for a site."""
    result = await db.execute(
        select(Geofence).where(Geofence.site_id == site.id)
    )
    return result.scalars().all()


@router.post("", response_model=GeofenceResponse, status_code=status.HTTP_201_CREATED)
async def create_geofence(
    geofence_data: GeofenceCreate,
    site: Site = Depends(verify_site_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new geofence for a site."""
    geofence = Geofence(
        site_id=site.id,
        name=geofence_data.name,
        polygon=geofence_data.polygon,
        center_lat=str(geofence_data.center_lat) if geofence_data.center_lat else None,
        center_lon=str(geofence_data.center_lon) if geofence_data.center_lon else None,
        radius_meters=str(geofence_data.radius_meters) if geofence_data.radius_meters else None,
    )
    db.add(geofence)
    await db.commit()
    await db.refresh(geofence)
    return geofence


@router.get("/{geofence_id}", response_model=GeofenceResponse)
async def get_geofence(
    geofence_id: UUID,
    site: Site = Depends(verify_site_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific geofence."""
    result = await db.execute(
        select(Geofence).where(
            Geofence.id == geofence_id,
            Geofence.site_id == site.id
        )
    )
    geofence = result.scalar_one_or_none()
    if not geofence:
        raise HTTPException(status_code=404, detail="Geofence not found")
    return geofence


@router.put("/{geofence_id}", response_model=GeofenceResponse)
async def update_geofence(
    geofence_id: UUID,
    geofence_data: GeofenceUpdate,
    site: Site = Depends(verify_site_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update a geofence."""
    result = await db.execute(
        select(Geofence).where(
            Geofence.id == geofence_id,
            Geofence.site_id == site.id
        )
    )
    geofence = result.scalar_one_or_none()
    if not geofence:
        raise HTTPException(status_code=404, detail="Geofence not found")
    
    if geofence_data.name is not None:
        geofence.name = geofence_data.name
    if geofence_data.polygon is not None:
        geofence.polygon = geofence_data.polygon
    if geofence_data.center_lat is not None:
        geofence.center_lat = str(geofence_data.center_lat)
    if geofence_data.center_lon is not None:
        geofence.center_lon = str(geofence_data.center_lon)
    if geofence_data.radius_meters is not None:
        geofence.radius_meters = str(geofence_data.radius_meters)
    if geofence_data.is_active is not None:
        geofence.is_active = geofence_data.is_active
    
    await db.commit()
    await db.refresh(geofence)
    return geofence


@router.delete("/{geofence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_geofence(
    geofence_id: UUID,
    site: Site = Depends(verify_site_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete a geofence."""
    result = await db.execute(
        select(Geofence).where(
            Geofence.id == geofence_id,
            Geofence.site_id == site.id
        )
    )
    geofence = result.scalar_one_or_none()
    if not geofence:
        raise HTTPException(status_code=404, detail="Geofence not found")
    
    await db.delete(geofence)
    await db.commit()
