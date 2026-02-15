from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from enum import Enum


class FilterMode(str, Enum):
    DISABLED = "disabled"
    IP = "ip"
    GEO = "geo"
    IP_AND_GEO = "ip_and_geo"


class SiteUserRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    VIEWER = "viewer"


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    id: UUID
    is_active: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[UUID] = None


class SiteBase(BaseModel):
    name: str
    hostname: Optional[str] = None
    path_prefix: str = "/"


class SiteCreate(SiteBase):
    filter_mode: FilterMode = FilterMode.DISABLED


class SiteUpdate(BaseModel):
    name: Optional[str] = None
    hostname: Optional[str] = None
    path_prefix: Optional[str] = None
    filter_mode: Optional[FilterMode] = None
    block_page_title: Optional[str] = None
    block_page_message: Optional[str] = None


class SiteResponse(SiteBase):
    id: UUID
    owner_user_id: UUID
    filter_mode: FilterMode
    block_page_title: str
    block_page_message: str
    created_at: datetime
    updated_at: datetime
    my_role: Optional[str] = None

    class Config:
        from_attributes = True


class GeofenceBase(BaseModel):
    name: Optional[str] = None
    polygon: Optional[dict] = None  # GeoJSON
    center_lat: Optional[float] = None
    center_lon: Optional[float] = None
    radius_meters: Optional[int] = None


class GeofenceCreate(GeofenceBase):
    pass


class GeofenceUpdate(BaseModel):
    name: Optional[str] = None
    polygon: Optional[dict] = None
    center_lat: Optional[float] = None
    center_lon: Optional[float] = None
    radius_meters: Optional[int] = None
    is_active: Optional[bool] = None


class GeofenceResponse(GeofenceBase):
    id: UUID
    site_id: UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class IPRuleBase(BaseModel):
    cidr: str
    action: str = Field(..., pattern="^(allow|deny)$")
    description: Optional[str] = None


class IPRuleCreate(IPRuleBase):
    priority: int = 0


class IPRuleUpdate(BaseModel):
    cidr: Optional[str] = None
    action: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


class IPRuleResponse(IPRuleBase):
    id: UUID
    site_id: UUID
    is_active: bool
    priority: int
    created_at: datetime

    class Config:
        from_attributes = True


class SiteUserBase(BaseModel):
    user_id: UUID
    role: SiteUserRole


class SiteUserCreate(SiteUserBase):
    pass


class SiteUserResponse(SiteUserBase):
    id: UUID
    site_id: UUID
    created_at: datetime
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True


class AccessAuditResponse(BaseModel):
    id: UUID
    site_id: UUID
    timestamp: datetime
    client_ip: Optional[str]
    ip_geo_country: Optional[str]
    ip_geo_city: Optional[str]
    ip_geo_lat: Optional[str]
    ip_geo_lon: Optional[str]
    client_gps_lat: Optional[str]
    client_gps_lon: Optional[str]
    decision: str
    reason: Optional[str]
    user_agent: Optional[str]
    artifact_path: Optional[str]

    class Config:
        from_attributes = True


class AccessAuditSearch(BaseModel):
    site_id: Optional[UUID] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    decision: Optional[str] = None
    client_ip: Optional[str] = None
    limit: int = 100
    offset: int = 0


class FilterConfig(BaseModel):
    filter_mode: FilterMode
    geofence: Optional[GeofenceCreate] = None
    ip_rules: Optional[List[IPRuleCreate]] = None
