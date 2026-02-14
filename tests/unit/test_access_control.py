import pytest
from app.services.access_control import access_control_service
from app.services.ip_rules import IPRuleData

@pytest.mark.anyio
async def test_ip_rules_precedence_is_deterministic():
    rules = [
        IPRuleData(cidr="10.0.0.0/8", action="deny"),
        IPRuleData(cidr="10.0.0.5/32", action="allow"),
    ]
    decision = await access_control_service.evaluate_access(
        filter_mode="ip",
        client_ip="10.0.0.5",
        client_gps_lat=None,
        client_gps_lon=None,
        ip_rules=rules,
        geofences_data=[]
    )
    assert decision.allowed is True
    assert "10.0.0.5" in decision.reason
