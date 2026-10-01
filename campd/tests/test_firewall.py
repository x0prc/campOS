from campd.config import FirewallConfig
from campd.firewall import add_domain_elements, apply, render_ruleset


class RecordingRunner:
    def __init__(self):
        self.calls = []

    def __call__(self, cmd, **kwargs):
        self.calls.append((cmd, kwargs))

        class Result:
            returncode = 0
            stdout = b""

        return Result()


def test_default_deny_policy():
    ruleset = render_ruleset(FirewallConfig(default_deny=True))
    assert "policy drop" in ruleset
    assert "table inet campd" in ruleset
    assert 'log prefix "campd-denied: "' in ruleset


def test_allow_when_deny_disabled():
    ruleset = render_ruleset(FirewallConfig(default_deny=False))
    assert "policy accept" in ruleset


def test_baseline_allows_dns_and_dhcp():
    ruleset = render_ruleset(FirewallConfig(), dns_listen="127.0.0.53",
                             dns_port=5353)
    assert "udp dport 67 accept" in ruleset
    assert "ip daddr 127.0.0.53 udp dport 5353 accept" in ruleset
    assert "ct state established,related accept" in ruleset


def test_domain_grants_declare_sets():
    cfg = FirewallConfig(allowed_domains=["cdn.example.com"])
    ruleset = render_ruleset(cfg)
    assert "set allow_v4 { type ipv4_addr; }" in ruleset
    assert "set allow_v6 { type ipv6_addr; }" in ruleset
    assert "ip daddr @allow_v4 accept" in ruleset
    assert "ip6 daddr @allow_v6 accept" in ruleset


def test_no_sets_when_no_domain_grants():
    ruleset = render_ruleset(FirewallConfig())
    assert "set allow" not in ruleset
    assert "@allow" not in ruleset


def test_uid_grants_rendered():
    ruleset = render_ruleset(FirewallConfig(allowed_outbound_uids=[101]))
    assert "meta skuid 101 accept" in ruleset


def test_baseline_allows_resolver_upstream_but_not_others():
    ruleset = render_ruleset(FirewallConfig())
    assert "meta skuid dnsmasq accept" in ruleset
    # apps get local resolver only
    assert "ip daddr 127.0.0.1 udp dport 53 accept" in ruleset


def test_apply_is_idempotent():
    runner = RecordingRunner()
    apply("table inet campd { }", runner=runner)
    assert runner.calls[0][0] == ["nft", "delete", "table", "inet", "campd"]
    assert runner.calls[0][1].get("check") is False
    assert runner.calls[1][0] == ["nft", "-f", "-"]
    assert runner.calls[1][1]["input"]


def test_add_domain_elements_resolves_and_inserts():
    def fake_resolver(host, *args):
        if host == "cdn.example.com":
            return [(2, 1, 6, "", ("93.184.216.34", 443)),
                    (10, 1, 6, "", ("2606:2800:220:1:248:1893:25c8:1946", 443))]
        raise OSError("nxdomain")

    runner = RecordingRunner()
    added = add_domain_elements(
        ["cdn.example.com", "gone.example.com"], runner=runner,
        resolver=fake_resolver,
    )
    assert added == 2
    cmds = [c for c, _ in runner.calls]
    v4 = next(c for c in cmds if "allow_v4" in c)
    assert "93.184.216.34" in v4[-1]
    v6 = next(c for c in cmds if "allow_v6" in c)
    assert "2606:2800" in v6[-1]


def test_add_domain_elements_empty_is_noop():
    runner = RecordingRunner()
    assert add_domain_elements([], runner=runner) == 0
    assert runner.calls == []
