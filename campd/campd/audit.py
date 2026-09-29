"""Connection audit log.

Parses nftables log lines (group 1, prefix "campd-denied: ") written by the
output chain and stores structured entries for the settings UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

LOG_PREFIX = "campd-denied:"
DEFAULT_LOG_PATH = Path("/var/log/campd/denied.log")


@dataclass
class DeniedEntry:
    src_ip: str
    dst_ip: str
    dport: int
    proto: str
    verdict: str  # e.g. "drop"
    raw: str


def parse_denied_line(line: str) -> DeniedEntry | None:
    """Parse one kernel/nft log line; returns None if not a campd line."""
    if LOG_PREFIX not in line:
        return None
    fields = _kv_pairs(line)
    return DeniedEntry(
        src_ip=fields.get("SRC", ""),
        dst_ip=fields.get("DST", ""),
        dport=int(fields.get("DPT", "0") or 0),
        proto=fields.get("PROTO", ""),
        verdict=fields.get("VERDICT", "drop"),
        raw=line.rstrip("\n"),
    )


def tail_denied(path: Path = DEFAULT_LOG_PATH, limit: int = 100) -> list[DeniedEntry]:
    if not path.exists():
        return []
    entries = []
    with path.open() as f:
        for line in f:
            entry = parse_denied_line(line)
            if entry:
                entries.append(entry)
    return entries[-limit:]


def _kv_pairs(line: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for token in line.replace(",", " ").split():
        if "=" in token:
            key, _, value = token.partition("=")
            out[key.upper()] = value
    return out
