import pytest
from app.services.ip_rules import ip_rules_service, IPRuleData


class TestIPRulesService:
    """Tests for IP rules evaluation logic."""

    def test_ip_matches_cidr_exact(self):
        """Test exact IP match."""
        assert ip_rules_service._ip_matches_cidr("192.168.1.1", "192.168.1.1") is True

    def test_ip_matches_cidr_range(self):
        """Test IP within CIDR range."""
        assert ip_rules_service._ip_matches_cidr("192.168.1.50", "192.168.1.0/24") is True

    def test_ip_matches_cidr_outside(self):
        """Test IP outside CIDR range."""
        assert ip_rules_service._ip_matches_cidr("192.168.2.1", "192.168.1.0/24") is False

    def test_ip_matches_cidr_ipv6(self):
        """Test IPv6 CIDR matching."""
        assert ip_rules_service._ip_matches_cidr("2001:db8::1", "2001:db8::/32") is True

    def test_evaluate_ip_rules_allow(self):
        """Test IP rules with allow rule matching."""
        rules = [
            IPRuleData(cidr="192.168.1.0/24", action="allow"),
        ]
        result, reason = ip_rules_service.evaluate_ip_rules(rules, "192.168.1.50")
        assert result is True

    def test_evaluate_ip_rules_deny(self):
        """Test IP rules with deny rule matching."""
        rules = [
            IPRuleData(cidr="10.0.0.0/8", action="deny"),
        ]
        result, reason = ip_rules_service.evaluate_ip_rules(rules, "10.1.2.3")
        assert result is False

    def test_evaluate_ip_rules_default_deny(self):
        """Test default deny when no rules match."""
        rules = [
            IPRuleData(cidr="192.168.1.0/24", action="allow"),
        ]
        result, reason = ip_rules_service.evaluate_ip_rules(rules, "172.16.0.1")
        assert result is False

    def test_evaluate_ip_rules_no_rules(self):
        """Test when no rules configured."""
        result, reason = ip_rules_service.evaluate_ip_rules([], "192.168.1.1")
        assert result is True
        assert "no IP rules" in reason

    def test_evaluate_ip_rules_priority(self):
        """Test that lower priority number comes first."""
        rules = [
            IPRuleData(cidr="0.0.0.0/0", action="allow", priority=10),
            IPRuleData(cidr="192.168.1.0/24", action="deny", priority=1),
        ]
        result, reason = ip_rules_service.evaluate_ip_rules(rules, "192.168.1.50")
        assert result is False
        assert "deny" in reason

    def test_parse_cidr_valid(self):
        """Test valid CIDR validation."""
        assert ip_rules_service.parse_cidr("192.168.1.0/24") is True
        assert ip_rules_service.parse_cidr("10.0.0.1") is True
        assert ip_rules_service.parse_cidr("2001:db8::/32") is True

    def test_parse_cidr_invalid(self):
        """Test invalid CIDR validation."""
        assert ip_rules_service.parse_cidr("invalid") is False
        assert ip_rules_service.parse_cidr("256.1.1.1") is False
