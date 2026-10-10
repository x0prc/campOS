"""Configuration loading for campd."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG_PATH = Path("/etc/campd/campd.toml")


@dataclass
class FirewallConfig:
    default_deny: bool = True
    allowed_outbound_uids: list[int] = field(default_factory=list)
    allowed_domains: list[str] = field(default_factory=list)


@dataclass
class MicConfig:
    kill_switch: bool = False
    block_usb_mics: bool = True
    block_internal_mics: bool = True


@dataclass
class DnsConfig:
    # Sources: local file paths or http(s) URLs. URL lists are downloaded
    # by `campctl dns fetch` (needs egress) into a cache; `apply` at boot
    # renders from cache only. Default: StevenBlack hosts — the de-facto
    # standard adware/malware list; swap for stricter lists in campd.toml.
    blocklists: list[str] = field(
        default_factory=lambda: [
            "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
        ]
    )
    listen: str = "127.0.0.1"
    port: int = 53
    # Explicit upstreams (dnsmasq no-resolv) so forwarding never loops back
    # through /etc/resolv.conf (which points apps at the local resolver).
    # Default: Quad9 — privacy-respecting, malware-blocking; override in
    # campd.toml.
    upstream: list[str] = field(
        default_factory=lambda: ["9.9.9.9", "149.112.112.112"]
    )


@dataclass
class WaydroidConfig:
    auto_freeze: bool = True
    freeze_delay_s: int = 60


@dataclass
class CampConfig:
    firewall: FirewallConfig = field(default_factory=FirewallConfig)
    mic: MicConfig = field(default_factory=MicConfig)
    dns: DnsConfig = field(default_factory=DnsConfig)
    waydroid: WaydroidConfig = field(default_factory=WaydroidConfig)


def load_config(path: Path | None = None) -> CampConfig:
    """Load config from TOML file; missing file yields defaults."""
    path = path or DEFAULT_CONFIG_PATH
    if not path.exists():
        return CampConfig()
    with path.open("rb") as f:
        data = tomllib.load(f)
    return CampConfig(
        firewall=FirewallConfig(**data.get("firewall", {})),
        mic=MicConfig(**data.get("mic", {})),
        dns=DnsConfig(**data.get("dns", {})),
        waydroid=WaydroidConfig(**data.get("waydroid", {})),
    )
