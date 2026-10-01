"""Runtime probes: verify what is *actually* enforced, not what config says.

Every probe degrades to an explicit "unavailable" on machines missing the
tool (dev laptops), so `campctl status` never crashes.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .dns import DNMASQ_CONF_PATH
from .mic import UDEV_RULES_PATH


def probe_firewall(*, runner=subprocess.run) -> str:
    """Is the campd nft table loaded? active | inactive | unavailable."""
    try:
        result = runner(["nft", "list", "table", "inet", "campd"],
                        capture_output=True, check=False)
    except (FileNotFoundError, OSError):
        return "unavailable"
    return "active" if result.returncode == 0 else "inactive"


def probe_dns(path: Path = DNMASQ_CONF_PATH) -> str:
    """configured | absent — is the campd dnsmasq drop-in in place?"""
    return "configured" if path.exists() else "absent"


def probe_mic_rules(path: Path = UDEV_RULES_PATH) -> str:
    """installed | absent — are kill-switch udev rules on disk?"""
    return "installed" if path.exists() else "absent"


def probe_waydroid(*, runner=subprocess.run) -> str:
    """running | frozen | stopped | unknown | unavailable."""
    try:
        result = runner(["lxc-info", "-n", "waydroid", "-sH"],
                        capture_output=True, check=False, text=True)
    except (FileNotFoundError, OSError):
        return "unavailable"
    out = (result.stdout or "").strip().lower()
    if "running" in out:
        return "running"
    if "frozen" in out:
        return "frozen"
    if "stopped" in out:
        return "stopped"
    return "unknown"
