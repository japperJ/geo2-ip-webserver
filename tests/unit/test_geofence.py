import pytest
from app.services.geofence import geofence_service, Point


class TestGeofenceService:
    """Tests for geofence evaluation logic."""

    def test_point_in_polygon_inside(self):
        """Test point inside a simple polygon."""
        polygon = {
            "type": "Polygon",
            "coordinates": [[
                [0, 0], [4, 0], [4, 4], [0, 4], [0, 0]
            ]]
        }
        result, reason = geofence_service.evaluate_geofence(
            polygon,
            client_lat=2,
            client_lon=2
        )
        assert result is True

    def test_point_in_polygon_outside(self):
        """Test point outside a polygon."""
        polygon = {
            "type": "Polygon",
            "coordinates": [[
                [0, 0], [4, 0], [4, 4], [0, 4], [0, 0]
            ]]
        }
        result, reason = geofence_service.evaluate_geofence(
            polygon,
            client_lat=5,
            client_lon=5
        )
        assert result is False

    def test_point_in_circle_inside(self):
        """Test point inside a circle geofence."""
        geofence = {
            "center_lat": "51.5074",
            "center_lon": "-0.1278",
            "radius_meters": "5000"
        }
        result, reason = geofence_service.evaluate_geofence(
            geofence,
            client_lat=51.51,
            client_lon=-0.12
        )
        assert result is True

    def test_point_in_circle_outside(self):
        """Test point outside a circle geofence."""
        geofence = {
            "center_lat": "51.5074",
            "center_lon": "-0.1278",
            "radius_meters": "1000"
        }
        result, reason = geofence_service.evaluate_geofence(
            geofence,
            client_lat=52.0,
            client_lon=-0.2
        )
        assert result is False

    def test_no_location_provided(self):
        """Test when no location is provided."""
        result, reason = geofence_service.evaluate_geofence(
            {"polygon": {"type": "Polygon", "coordinates": [[[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]]]}},
            client_lat=None,
            client_lon=None
        )
        assert result is False
        assert "No location" in reason

    def test_haversine_distance_calculation(self):
        """Test haversine distance calculation."""
        point1 = Point(51.5074, -0.1278)
        point2 = Point(51.5074, -0.1278)
        
        distance = geofence_service._haversine_distance(point1, point2)
        assert distance == 0

    def test_haversine_distance_known_points(self):
        """Test haversine with known distance (London to Paris ~344km)."""
        london = Point(51.5074, -0.1278)
        paris = Point(48.8566, 2.3522)
        
        distance = geofence_service._haversine_distance(london, paris)
        assert 340000 < distance < 350000
