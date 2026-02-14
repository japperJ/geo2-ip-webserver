import ipaddress
import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class IPRuleData:
    cidr: str
    action: str


class IPRulesService:
    def evaluate_ip_rules(
        self,
        ip_rules: List[IPRuleData],
        client_ip: str,
        ip_geo: Optional[dict] = None,
    ) -> tuple[bool, str]:
        """
        Evaluate IP rules for a client.
        Returns (allowed, reason).
        Rules are evaluated by specificity (most specific CIDR first).
        """
        if not ip_rules:
            return True, "no IP rules configured"

        # Find all matching rules
        matching_rules = []
        for rule in ip_rules:
            try:
                if self._ip_matches_cidr(client_ip, rule.cidr):
                    matching_rules.append(rule)
            except Exception as e:
                logger.error(f"Error evaluating IP rule {rule.cidr}: {e}")
                continue

        if not matching_rules:
            # Default deny if no rules matched
            return False, "no matching IP rule"

        # Sort by specificity (most specific first = highest prefix length)
        sorted_rules = self._sort_by_specificity(matching_rules)

        # Return the first matching rule (most specific)
        rule = sorted_rules[0]
        is_allowed = rule.action == "allow"
        return is_allowed, f"matched rule {rule.cidr} ({rule.action})"

    def _sort_by_specificity(self, rules: List[IPRuleData]) -> List[IPRuleData]:
        """Sort rules by CIDR specificity (most specific first)."""
        def get_prefix_length(rule: IPRuleData) -> int:
            """Get the prefix length from a CIDR. Higher = more specific."""
            cidr = rule.cidr
            if "/" not in cidr:
                # Single IP = /32 for IPv4 or /128 for IPv6
                try:
                    addr = ipaddress.ip_address(cidr)
                    return 128 if addr.version == 6 else 32
                except ValueError:
                    return 0
            try:
                network = ipaddress.ip_network(cidr, strict=False)
                return network.prefixlen
            except ValueError:
                return 0
        
        return sorted(rules, key=get_prefix_length, reverse=True)

    def _ip_matches_cidr(self, ip: str, cidr: str) -> bool:
        """Check if IP matches CIDR pattern."""
        try:
            # Handle single IP
            if "/" not in cidr:
                return ip == cidr
            
            # Parse CIDR
            network = ipaddress.ip_network(cidr, strict=False)
            return ipaddress.ip_address(ip) in network
        except ValueError as e:
            logger.error(f"Invalid CIDR pattern {cidr}: {e}")
            return False

    def parse_cidr(self, cidr: str) -> bool:
        """Validate a CIDR pattern."""
        try:
            if "/" not in cidr:
                ipaddress.ip_address(cidr)
            else:
                ipaddress.ip_network(cidr, strict=False)
            return True
        except ValueError:
            return False


ip_rules_service = IPRulesService()
