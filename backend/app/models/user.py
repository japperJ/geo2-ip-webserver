import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSON
import enum

from app.db.session import Base


class FilterMode(str, enum.Enum):
    DISABLED = "disabled"
    IP = "ip"
    GEO = "geo"
    IP_AND_GEO = "ip_and_geo"


class SiteUserRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Site(Base):
    __tablename__ = "sites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    hostname = Column(String(255), unique=True, index=True)
    path_prefix = Column(String(100), default="/")
    owner_user_id = Column(UUID(as_uuid=True), nullable=False)
    filter_mode = Column(SQLEnum(FilterMode, native_enum=False, values_callable=lambda x: [e.value for e in x]), default=FilterMode.DISABLED)
    block_page_title = Column(String(255), default="Access Denied")
    block_page_message = Column(String(1000), default="Your location or IP address does not meet the access requirements for this site.")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SiteUser(Base):
    __tablename__ = "site_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    site_id = Column(UUID(as_uuid=True), nullable=False)
    role = Column(SQLEnum(SiteUserRole, native_enum=False, values_callable=lambda x: [e.value for e in x]), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Geofence(Base):
    __tablename__ = "geofences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String(255))
    polygon = Column(JSON)  # GeoJSON format
    center_lat = Column(String(50))
    center_lon = Column(String(50))
    radius_meters = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IPRule(Base):
    __tablename__ = "ip_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(UUID(as_uuid=True), nullable=False)
    cidr = Column(String(50), nullable=False)
    action = Column(String(10), nullable=False)  # "allow" or "deny"
    description = Column(String(500))
    is_active = Column(Boolean, default=True)
    priority = Column(String(10), default="0")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AccessAudit(Base):
    __tablename__ = "access_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(UUID(as_uuid=True), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    client_ip = Column(String(50))
    ip_geo_country = Column(String(10))
    ip_geo_city = Column(String(100))
    ip_geo_lat = Column(String(50))
    ip_geo_lon = Column(String(50))
    client_gps_lat = Column(String(50))
    client_gps_lon = Column(String(50))
    decision = Column(String(20))  # "allowed" or "blocked"
    reason = Column(String(500))
    user_agent = Column(String(500))
    artifact_path = Column(String(500))
    artifact_s3_key = Column(String(500))
