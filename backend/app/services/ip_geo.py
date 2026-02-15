import asyncio
import logging
from typing import Optional
import aiohttp
import redis.asyncio as redis
from datetime import timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)


class IPGeoService:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.cache_ttl = 3600  # 1 hour

    async def get_redis(self):
        if self.redis_client is None:
            self.redis_client = await redis.from_url(settings.REDIS_URL)
        return self.redis_client

    async def lookup_ip_geo(self, ip_address: str) -> Optional[dict]:
        """Look up geolocation for an IP address with caching."""
        if not ip_address:
            return None

        # Check private IPs - no geo lookup needed
        if self._is_private_ip(ip_address):
            return {
                "country": "XX",
                "city": "Private",
                "lat": None,
                "lon": None,
                "is_private": True,
            }

        cache_key = f"ip_geo:{ip_address}"
        
        try:
            redis_client = await self.get_redis()
            cached = await redis_client.get(cache_key)
            if cached:
                import json
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis cache lookup failed: {e}")

        # Perform lookup (simulated - in production use MaxMind or IPinfo)
        geo_data = await self._lookup_ip(ip_address)

        if geo_data:
            try:
                redis_client = await self.get_redis()
                import json
                await redis_client.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(geo_data)
                )
            except Exception as e:
                logger.warning(f"Redis cache set failed: {e}")

        return geo_data

    async def _lookup_ip(self, ip_address: str) -> Optional[dict]:
        """Actual IP geolocation lookup. Override with real implementation."""
        # This is a placeholder - in production, use MaxMind GeoIP2 or IPinfo API
        # For now, return mock data based on IP ranges for testing
        return {
            "country": "US",
            "city": "San Francisco",
            "lat": 37.7749,
            "lon": -122.4194,
            "is_private": False,
        }

    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP is private/reserved."""
        if ip.startswith("127.") or ip == "localhost":
            return True
        if ip.startswith("10."):
            return True
        if ip.startswith("192.168."):
            return True
        if ip.startswith("172.16."):
            return True
        if ip.startswith("172.17.") or ip.startswith("172.18.") or ip.startswith("172.19."):
            return True
        if ip.startswith("172.2") or ip.startswith("172.30.") or ip.startswith("172.31."):
            return True
        return False

    async def close(self):
        if self.redis_client:
            await self.redis_client.close()


ip_geo_service = IPGeoService()
