"""Default-deny egress firewall (nftables) rule generation and application.

The ruleset is generated as text so it can be unit-tested without root or
nftables present; ``apply()`` shells out to ``nft``.
"""

from __future__ import annotations

import subprocess

from .config import FirewallConfig

TABLE = "campd"
CHAIN = "output"

BASELINE_RULES = """\
# loopback
meta iifname "lo" accept
# DHCP out
udp sport 68 udp dport 67 accept
# DNS only to the local resolver
ip daddr {dns_listen} udp dport {dns_port} accept
ip daddr {dns_listen} tcp dport {dns_port} accept
# NTP (default pool; kept minimal on purpose)
udp dport 123 accept
# established sessions
ct state established,related accept
ct state invalid drop
"""


def render_ruleset(cfg: FirewallConfig, dns_listen: str = "127.0.0.1",
                   dns_port: int = 53) -> str:
    """Render the campd nftables ruleset for the inet family."""
    policy = "accept" if not cfg.default_deny else "drop"
    rules = BASELINE_RULES.format(dns_listen=dns_listen, dns_port=dns_port)
    for uid in cfg.allowed_outbound_uids:
        rules += f"meta skuid {uid} accept\n"
    for domain in cfg.allowed_domains:
        # Domain-based rules are enforced via the local resolver; here we
        # accept traffic to resolved allowlist sets (populated by campd).
        rules += f"ip daddr @allow_{_setname(domain)} accept\n"
    return (
        f"table inet {TABLE} {{\n"
        f"  chain {CHAIN} {{\n"
        f"    type filter hook output priority 0; policy {policy};\n"
        f"{_indent(rules)}"
        f"    log prefix \"campd-denied: \" group 1\n"
        f"  }}\n"
        f"}}\n"
    )


def apply(ruleset: str) -> None:
    """Apply a rendered ruleset atomically (requires root + nftables)."""
    subprocess.run(
        ["nft", "-f", "-"],
        input=ruleset.encode(),
        check=True,
    )


def _setname(domain: str) -> str:
    return domain.replace(".", "_").replace("-", "_")


def _indent(text: str, prefix: str = "    ") -> str:
    return "".join(prefix + line + "\n" for line in text.splitlines())
