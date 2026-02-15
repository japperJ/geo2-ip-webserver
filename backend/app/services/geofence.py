import math
import logging
from typing import Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Point:
    lat: float
    lon: float


class GeofenceService:
    def evaluate_geofence(
        self,
        geofence_data: dict,
        client_lat: Optional[float] = None,
        client_lon: Optional[float] = None,
    ) -> tuple[bool, str]:
        """
        Evaluate if client location is within geofence.
        Returns (allowed, reason).
        """
        if client_lat is None or client_lon is None:
            return False, "No location provided"

        client_point = Point(client_lat, client_lon)

        # Check for polygon geofence
        if geofence_data.get("polygon"):
            is_inside = self._point_in_polygon(
                client_point,
                geofence_data["polygon"]
            )
            return is_inside, "inside polygon" if is_inside else "outside polygon"

        # Check for circle/radius geofence
        if geofence_data.get("center_lat") and geofence_data.get("center_lon") and geofence_data.get("radius_meters"):
            center = Point(
                float(geofence_data["center_lat"]),
                float(geofence_data["center_lon"])
            )
            radius = float(geofence_data["radius_meters"])
            distance = self._haversine_distance(client_point, center)
            is_inside = distance <= radius
            return is_inside, f"within {radius}m" if is_inside else f"outside {radius}m radius"

        # No geofence configured
        return True, "no geofence configured"

    def _point_in_polygon(self, point: Point, polygon: dict) -> bool:
        """Check if point is inside a GeoJSON polygon."""
        try:
            if polygon.get("type") == "Polygon":
                coords = polygon["coordinates"][0]  # Outer ring
                return self._ray_cast(point, coords)
            return False
        except Exception as e:
            logger.error(f"Polygon evaluation error: {e}")
            return False

    def _ray_cast(self, point: Point, polygon_coords: List[List[float]]) -> bool:
        """Ray casting algorithm for point in polygon."""
        x, y = point.lon, point.lat
        n = len(polygon_coords)
        inside = False

        j = n - 1
        for i in range(n):
            xi, yi = polygon_coords[i]
            xj, yj = polygon_coords[j]

            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i

        return inside

    def _haversine_distance(self, point1: Point, point2: Point) -> float:
        """Calculate distance between two points in meters using Haversine formula."""
        R = 6371000  # Earth's radius in meters

        lat1 = math.radians(point1.lat)
        lat2 = math.radians(point2.lat)
        delta_lat = math.radians(point2.lat - point1.lat)
        delta_lon = math.radians(point2.lon - point1.lon)

        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1) * math.cos(lat2) *
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c


geofence_service = GeofenceService()
