from campd.config import FirewallConfig
from campd.firewall import render_ruleset


def test_default_deny_policy():
    ruleset = render_ruleset(FirewallConfig(default_deny=True))
    assert "policy drop" in ruleset
    assert "table inet campd" in ruleset


def test_allow_when_deny_disabled():
    ruleset = render_ruleset(FirewallConfig(default_deny=False))
    assert "policy accept" in ruleset


def test_baseline_allows_dns_and_dhcp():
    ruleset = render_ruleset(FirewallConfig(), dns_listen="127.0.0.53",
                             dns_port=5353)
    assert "udp dport 67 accept" in ruleset
    assert "ip daddr 127.0.0.53 udp dport 5353 accept" in ruleset
    assert "ct state established,related accept" in ruleset


def test_uid_grants_rendered():
    cfg = FirewallConfig(allowed_outbound_uids=[101])
    ruleset = render_ruleset(cfg)
    assert "meta skuid 101 accept" in ruleset


def test_domain_grants_rendered_as_sets():
    cfg = FirewallConfig(allowed_domains=["cdn.example.com"])
    ruleset = render_ruleset(cfg)
    assert "ip daddr @allow_cdn_example_com accept" in ruleset


def test_denied_traffic_is_logged():
    ruleset = render_ruleset(FirewallConfig())
    assert 'log prefix "campd-denied: "' in ruleset
