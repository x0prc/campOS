"""Connection audit log.

Parses nftables log lines (group 1, prefix "campd-denied: ") written by the
output chain and stores structured entries for the settings UI.
"""

from __future__ import annotations

import subprocess
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


def tail_denied(path: Path | None = None, limit: int = 100) -> list[DeniedEntry]:
    path = path or DEFAULT_LOG_PATH
    if not path.exists():
        return []
    entries = []
    with path.open() as f:
        for line in f:
            entry = parse_denied_line(line)
            if entry:
                entries.append(entry)
    return entries[-limit:]


def ingest_journal(*, since: str = "10 min ago",
                   log_path: Path | None = None,
                   runner=None) -> int:
    """Pull campd-denied lines from the kernel journal into the audit log.

    Deduplicates against lines already present. Returns number of new
    entries appended, or -1 if the journal is unavailable.
    """
    log_path = log_path or DEFAULT_LOG_PATH
    runner = runner or subprocess.run
    try:
        result = runner(
            ["journalctl", "-k", "-o", "cat", "--since", since],
            capture_output=True, check=False,
        )
    except (FileNotFoundError, OSError):
        return -1  # journal unavailable (dev machine)
    raw_out = result.stdout or b""
    if isinstance(raw_out, bytes):
        raw_out = raw_out.decode(errors="replace")

    existing: set[str] = set()
    if log_path.exists():
        existing = set(log_path.read_text().splitlines())

    new_lines: list[str] = []
    for line in raw_out.splitlines():
        entry = parse_denied_line(line)
        if entry and entry.raw not in existing:
            new_lines.append(entry.raw)
            existing.add(entry.raw)

    if new_lines:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a") as f:
            f.write("\n".join(new_lines) + "\n")
    return len(new_lines)


def format_entry(entry: DeniedEntry) -> str:
    return (f"{entry.src_ip} -> {entry.dst_ip}:{entry.dport} "
            f"{entry.proto} {entry.verdict}")


def _kv_pairs(line: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for token in line.replace(",", " ").split():
        if "=" in token:
            key, _, value = token.partition("=")
            out[key.upper()] = value
    return out
