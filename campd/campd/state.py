"""Persistent runtime state for campd.

The build-time policy lives in /etc/campd/campd.toml; mutations made at
runtime (mic kill, user firewall grants) live here so they survive reboot.
State is machine-written JSON — atomic replace on every save.

Path override: CAMPD_STATE_PATH (tests / dev machines).
Corrupt or missing state fails open to *build defaults* (privacy posture is
enforced by the firewall config, not by this file).
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field, asdict
from pathlib import Path

DEFAULT_STATE_PATH = Path("/var/lib/campd/state.json")


def state_path() -> Path:
    return Path(os.environ.get("CAMPD_STATE_PATH", str(DEFAULT_STATE_PATH)))


@dataclass
class RuntimeState:
    mic_kill: bool = False
    granted_uids: list[int] = field(default_factory=list)
    granted_domains: list[str] = field(default_factory=list)


def load_state(path: Path | None = None) -> RuntimeState:
    path = path or state_path()
    if not path.exists():
        return RuntimeState()
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return RuntimeState()
    return RuntimeState(
        mic_kill=bool(data.get("mic_kill", False)),
        granted_uids=[int(u) for u in data.get("granted_uids", [])],
        granted_domains=[str(d) for d in data.get("granted_domains", [])],
    )


def save_state(state: RuntimeState, path: Path | None = None) -> None:
    path = path or state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(asdict(state), f, indent=2)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def effective_firewall(cfg, state: RuntimeState):
    """Merge build config with runtime grants into a FirewallConfig."""
    fw_cfg = cfg.firewall
    uids = list(dict.fromkeys([*fw_cfg.allowed_outbound_uids, *state.granted_uids]))
    domains = list(dict.fromkeys([*fw_cfg.allowed_domains, *state.granted_domains]))
    return type(fw_cfg)(
        default_deny=fw_cfg.default_deny,
        allowed_outbound_uids=uids,
        allowed_domains=domains,
    )


def effective_mic(cfg, state: RuntimeState):
    """Mic kill is engaged if either build policy or runtime state says so."""
    mic = cfg.mic
    return type(mic)(
        kill_switch=mic.kill_switch or state.mic_kill,
        block_usb_mics=mic.block_usb_mics,
        block_internal_mics=mic.block_internal_mics,
    )
