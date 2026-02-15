from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User, Site, SiteUser, SiteUserRole
from app.schemas import SiteUserCreate, SiteUserResponse

router = APIRouter(prefix="/admin/sites/{site_id}/users", tags=["admin:site-users"])


async def verify_site_admin(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Site:
    """Verify user has admin access to site (owner or admin role)."""
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
            SiteUser.role.in_([SiteUserRole.OWNER, SiteUserRole.ADMIN])
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not authorized to manage this site")
    
    return site


async def verify_site_member(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Site:
    """Verify user is a member of the site (any role)."""
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
            SiteUser.user_id == current_user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this site")
    
    return site


@router.get("", response_model=List[SiteUserResponse])
async def list_site_users(
    site: Site = Depends(verify_site_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all users for a site."""
    result = await db.execute(
        select(SiteUser).where(SiteUser.site_id == site.id)
    )
    site_users = result.scalars().all()
    
    # Fetch user data for each site_user
    responses = []
    for su in site_users:
        user_result = await db.execute(
            select(User).where(User.id == su.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        su_dict = {
            "id": su.id,
            "user_id": su.user_id,
            "site_id": su.site_id,
            "role": su.role.value if hasattr(su.role, 'value') else su.role,
            "created_at": su.created_at,
            "user": user
        }
        responses.append(su_dict)
    
    return responses


@router.post("", response_model=SiteUserResponse, status_code=status.HTTP_201_CREATED)
async def add_site_user(
    user_data: SiteUserCreate,
    site: Site = Depends(verify_site_admin),
    db: AsyncSession = Depends(get_db)
):
    """Add a user to a site with a role."""
    result = await db.execute(
        select(User).where(User.id == user_data.user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = await db.execute(
        select(SiteUser).where(
            SiteUser.site_id == site.id,
            SiteUser.user_id == user_data.user_id
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="User already has access to this site")
    
    # Convert role to enum (lowercase)
    role_str = user_data.role.value if hasattr(user_data.role, 'value') else user_data.role
    role = SiteUserRole(role_str.lower())
    
    site_user = SiteUser(
        site_id=site.id,
        user_id=user_data.user_id,
        role=role,
    )
    db.add(site_user)
    await db.commit()
    await db.refresh(site_user)
    return site_user


@router.put("/{site_user_id}", response_model=SiteUserResponse)
async def update_site_user_role(
    site_user_id: UUID,
    role: str,
    site: Site = Depends(verify_site_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update a user's role on a site."""
    result = await db.execute(
        select(SiteUser).where(
            SiteUser.id == site_user_id,
            SiteUser.site_id == site.id
        )
    )
    site_user = result.scalar_one_or_none()
    
    if not site_user:
        raise HTTPException(status_code=404, detail="Site user not found")
    
    site_user.role = SiteUserRole(role.lower())
    await db.commit()
    await db.refresh(site_user)
    return site_user


@router.delete("/{site_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_site_user(
    site_user_id: UUID,
    site: Site = Depends(verify_site_admin),
    db: AsyncSession = Depends(get_db)
):
    """Remove a user from a site."""
    result = await db.execute(
        select(SiteUser).where(
            SiteUser.id == site_user_id,
            SiteUser.site_id == site.id
        )
    )
    site_user = result.scalar_one_or_none()
    
    if not site_user:
        raise HTTPException(status_code=404, detail="Site user not found")
    
    if site_user.role == SiteUserRole.OWNER:
        raise HTTPException(status_code=400, detail="Cannot remove site owner")
    
    await db.delete(site_user)
    await db.commit()
