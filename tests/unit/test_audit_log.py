import pytest
from app.services.audit_log import audit_log_service
from uuid import uuid4

@pytest.mark.anyio
async def test_public_access_creates_audit_log_entry(db_session):
    """Test that public access creates an audit log entry."""
    site_id = uuid4()
    
    # Create an audit log entry
    entry = await audit_log_service.log_public_access(
        db=db_session,
        site_id=site_id,
        client_ip="10.0.0.1",
        allowed=True,
        reason="ip_rule_allow"
    )
    
    # Verify the entry was created
    assert entry is not None
    assert entry.site_id == site_id
    assert entry.client_ip == "10.0.0.1"
    assert entry.decision == "allowed"
    assert entry.reason == "ip_rule_allow"
    
    # List entries
    result = await audit_log_service.list_entries(db_session, site_id=site_id, limit=1)
    assert len(result) > 0
    assert result[0].site_id == site_id
