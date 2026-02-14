import logging
from typing import Optional, List
from dataclasses import dataclass, asdict
from uuid import UUID

from app.services.ip_geo import ip_geo_service
from app.services.geofence import geofence_service, Point
from app.services.ip_rules import ip_rules_service, IPRuleData

logger = logging.getLogger(__name__)


@dataclass
class AccessDecision:
    allowed: bool
    reason: str
    ip_geo: Optional[dict] = None
    geo_check: Optional[str] = None
    ip_check: Optional[str] = None


class AccessControlService:
    def __init__(self):
        self.ip_geo = ip_geo_service
        self.geofence = geofence_service
        self.ip_rules = ip_rules_service

    async def evaluate_access(
        self,
        filter_mode: str,
        client_ip: str,
        client_gps_lat: Optional[float] = None,
        client_gps_lon: Optional[float] = None,
        ip_rules: Optional[List[IPRuleData]] = None,
        geofences_data: Optional[List[dict]] = None,
    ) -> AccessDecision:
        """
        Evaluate access based on filter mode.
        
        Args:
            filter_mode: One of "disabled", "ip", "geo", "ip_and_geo"
            client_ip: Client IP address
            client_gps_lat: Client GPS latitude (from browser)
            client_gps_lon: Client GPS longitude (from browser)
            ip_rules: List of IP rules for the site
            geofences_data: List of geofence configurations for the site
        """
        # Mode: disabled - allow all
        if filter_mode == "disabled":
            return AccessDecision(
                allowed=True,
                reason="filter disabled"
            )

        # Get IP geolocation
        ip_geo = await self.ip_geo.lookup_ip_geo(client_ip)

        # Evaluate based on mode
        if filter_mode == "ip":
            return await self._evaluate_ip_only(client_ip, ip_geo, ip_rules)
        
        if filter_mode == "geo":
            return self._evaluate_geo_only(
                client_gps_lat, client_gps_lon, ip_geo, geofences_data
            )
        
        if filter_mode == "ip_and_geo":
            return await self._evaluate_ip_and_geo(
                client_ip, client_gps_lat, client_gps_lon,
                ip_geo, ip_rules, geofences_data
            )

        # Unknown mode - allow by default
        return AccessDecision(
            allowed=True,
            reason=f"unknown filter mode: {filter_mode}"
        )

    async def _evaluate_ip_only(
        self,
        client_ip: str,
        ip_geo: Optional[dict],
        ip_rules: Optional[List[IPRuleData]],
    ) -> AccessDecision:
        """Evaluate IP-only filter mode."""
        allowed, reason = self.ip_rules.evaluate_ip_rules(
            ip_rules or [], client_ip, ip_geo
        )
        return AccessDecision(
            allowed=allowed,
            reason=reason,
            ip_geo=ip_geo,
            ip_check=reason
        )

    def _evaluate_geo_only(
        self,
        client_gps_lat: Optional[float],
        client_gps_lon: Optional[float],
        ip_geo: Optional[dict],
        geofences_data: Optional[List[dict]],
    ) -> AccessDecision:
        """Evaluate Geo-only filter mode - checks if client is within ANY geofence."""
        # Try client GPS first, then fall back to IP geo
        lat = client_gps_lat if client_gps_lat is not None else ip_geo.get("lat") if ip_geo else None
        lon = client_gps_lon if client_gps_lon is not None else ip_geo.get("lon") if ip_geo else None

        if lat is None or lon is None:
            return AccessDecision(
                allowed=False,
                reason="no location available",
                ip_geo=ip_geo
            )

        if not geofences_data:
            return AccessDecision(
                allowed=True,
                reason="no geofence configured",
                ip_geo=ip_geo
            )

        # Check if client is within ANY of the geofences
        for geofence_data in geofences_data:
            allowed, geo_reason = self.geofence.evaluate_geofence(
                geofence_data, lat, lon
            )
            if allowed:
                return AccessDecision(
                    allowed=True,
                    reason=f"within geofence: {geo_reason}",
                    ip_geo=ip_geo,
                    geo_check=geo_reason
                )

        # Not in any geofence
        return AccessDecision(
            allowed=False,
            reason="not within any configured geofence",
            ip_geo=ip_geo,
            geo_check="outside all geofences"
        )

    async def _evaluate_ip_and_geo(
        self,
        client_ip: str,
        client_gps_lat: Optional[float],
        client_gps_lon: Optional[float],
        ip_geo: Optional[dict],
        ip_rules: Optional[List[IPRuleData]],
        geofences_data: Optional[List[dict]],
    ) -> AccessDecision:
        """Evaluate IP + Geo filter mode (both must pass)."""
        # IP check
        ip_allowed, ip_reason = self.ip_rules.evaluate_ip_rules(
            ip_rules or [], client_ip, ip_geo
        )

        # Geo check - client must be within ANY geofence
        lat = client_gps_lat if client_gps_lat is not None else ip_geo.get("lat") if ip_geo else None
        lon = client_gps_lon if client_gps_lon is not None else ip_geo.get("lon") if ip_geo else None

        geo_allowed = False
        geo_reason = "no location available"
        
        if lat is not None and lon is not None:
            if geofences_data:
                # Check if within ANY geofence
                for geofence_data in geofences_data:
                    geo_allowed, geo_reason = self.geofence.evaluate_geofence(
                        geofence_data, lat, lon
                    )
                    if geo_allowed:
                        break
            else:
                geo_allowed = True
                geo_reason = "no geofence configured"

        # Both must pass
        allowed = ip_allowed and geo_allowed
        
        if not ip_allowed:
            reason = f"IP: {ip_reason}"
        elif not geo_allowed:
            reason = f"Geo: {geo_reason}"
        else:
            reason = "both IP and geo checks passed"

        return AccessDecision(
            allowed=allowed,
            reason=reason,
            ip_geo=ip_geo,
            ip_check=ip_reason,
            geo_check=geo_reason
        )


access_control_service = AccessControlService()
