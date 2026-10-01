"""Default-deny egress firewall (nftables) rule generation and application.

The ruleset is rendered as text so it can be unit-tested without root or
nftables present; ``apply()`` shells out to ``nft`` and is idempotent
(existing campd table is flushed first).

Domain grants are enforced via named address sets: ``apply()`` resolves
granted domains and adds the IPs as elements. Resolution is best-effort —
stale elements are a known limitation until a periodic re-resolve lands
(see ROADMAP).
"""

from __future__ import annotations

import socket
import subprocess

from .config import FirewallConfig

TABLE = "campd"
CHAIN = "output"

BASELINE_RULES = """\
# loopback
meta iifname "lo" accept
# DHCP out
udp sport 68 udp dport 67 accept
# apps -> local resolver only
ip daddr {dns_listen} udp dport {dns_port} accept
ip daddr {dns_listen} tcp dport {dns_port} accept
# upstream forwarding by campd's resolver (user "dnsmasq") and nothing else;
# TODO: redirect foreign :53 to the local resolver once uid mapping is stable
meta skuid dnsmasq accept
# NTP (kept minimal on purpose)
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
    if cfg.allowed_domains:
        rules += "ip daddr @allow_v4 accept\n"
        rules += "ip6 daddr @allow_v6 accept\n"

    sets = ""
    if cfg.allowed_domains:
        sets = (
            f"  set allow_v4 {{ type ipv4_addr; }}\n"
            f"  set allow_v6 {{ type ipv6_addr; }}\n"
        )
    return (
        f"table inet {TABLE} {{\n"
        f"{sets}"
        f"  chain {CHAIN} {{\n"
        f"    type filter hook output priority 0; policy {policy};\n"
        f"{_indent(rules)}"
        f"    log prefix \"campd-denied: \" group 1\n"
        f"  }}\n"
        f"}}\n"
    )


def apply(ruleset: str, *, runner=subprocess.run) -> None:
    """Apply a rendered ruleset atomically and idempotently (needs root)."""
    # Flush any existing table first so re-apply never fails on redefinition.
    runner(["nft", "delete", "table", "inet", TABLE], check=False)
    runner(["nft", "-f", "-"], input=ruleset.encode(), check=True)


def add_domain_elements(domains: list[str], *, runner=subprocess.run,
                        resolver=socket.getaddrinfo) -> int:
    """Resolve granted domains and add them to the allow sets.

    Best effort: unresolvable domains are skipped; returns count of
    elements added.
    """
    if not domains:
        return 0
    v4: set[str] = set()
    v6: set[str] = set()
    for domain in domains:
        try:
            infos = resolver(domain, 0, socket.SOCK_STREAM)
        except OSError:
            continue
        for info in infos:
            ip = info[4][0]
            (v6 if ":" in ip else v4).add(ip)

    added = 0
    for set_name, ips in (("allow_v4", v4), ("allow_v6", v6)):
        if not ips:
            continue
        spec = "{ " + ", ".join(sorted(ips)) + " }"
        try:
            runner(["nft", "add", "element", "inet", TABLE, set_name, spec],
                   check=False)
            added += len(ips)
        except (FileNotFoundError, OSError):
            break
    return added


def _indent(text: str, prefix: str = "    ") -> str:
    return "".join(prefix + line + "\n" for line in text.splitlines())
