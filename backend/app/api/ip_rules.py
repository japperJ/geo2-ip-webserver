from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User, Site, IPRule, SiteUser, SiteUserRole
from app.schemas import IPRuleCreate, IPRuleUpdate, IPRuleResponse

router = APIRouter(prefix="/admin/sites/{site_id}/ip-rules", tags=["admin:ip-rules"])


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


@router.get("", response_model=List[IPRuleResponse])
async def list_ip_rules(
    site: Site = Depends(verify_site_member),
    db: AsyncSession = Depends(get_db)
):
    """List all IP rules for a site."""
    result = await db.execute(
        select(IPRule).where(IPRule.site_id == site.id).order_by(IPRule.priority)
    )
    return result.scalars().all()


@router.get("/{rule_id}", response_model=IPRuleResponse)
async def get_ip_rule(
    rule_id: UUID,
    site: Site = Depends(verify_site_member),
    db: AsyncSession = Depends(get_db)
):
    """List all IP rules for a site."""
    result = await db.execute(
        select(IPRule).where(IPRule.site_id == site.id).order_by(IPRule.priority)
    )
    return result.scalars().all()


@router.post("", response_model=IPRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_ip_rule(
    rule_data: IPRuleCreate,
    site: Site = Depends(verify_site_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new IP rule for a site."""
    rule = IPRule(
        site_id=site.id,
        cidr=rule_data.cidr,
        action=rule_data.action,
        description=rule_data.description,
        priority=str(rule_data.priority) if rule_data.priority else "0",
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.get("/{rule_id}", response_model=IPRuleResponse)
async def get_ip_rule(
    rule_id: UUID,
    site: Site = Depends(verify_site_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific IP rule."""
    result = await db.execute(
        select(IPRule).where(
            IPRule.id == rule_id,
            IPRule.site_id == site.id
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="IP rule not found")
    return rule


@router.put("/{rule_id}", response_model=IPRuleResponse)
async def update_ip_rule(
    rule_id: UUID,
    rule_data: IPRuleUpdate,
    site: Site = Depends(verify_site_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update an IP rule."""
    result = await db.execute(
        select(IPRule).where(
            IPRule.id == rule_id,
            IPRule.site_id == site.id
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="IP rule not found")
    
    if rule_data.cidr is not None:
        rule.cidr = rule_data.cidr
    if rule_data.action is not None:
        rule.action = rule_data.action
    if rule_data.description is not None:
        rule.description = rule_data.description
    if rule_data.is_active is not None:
        rule.is_active = rule_data.is_active
    if rule_data.priority is not None:
        rule.priority = str(rule_data.priority)
    
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ip_rule(
    rule_id: UUID,
    site: Site = Depends(verify_site_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete an IP rule."""
    result = await db.execute(
        select(IPRule).where(
            IPRule.id == rule_id,
            IPRule.site_id == site.id
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="IP rule not found")
    
    await db.delete(rule)
    await db.commit()
