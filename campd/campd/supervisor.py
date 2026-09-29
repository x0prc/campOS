"""Waydroid lifecycle supervisor.

Starts the Android container on demand, freezes it when idle, and ensures
binder_linux is only loaded while the container runs.
"""

from __future__ import annotations

import subprocess
import time

from .config import WaydroidConfig

BINDER_MODULE = "binder_linux"


class Supervisor:
    def __init__(self, cfg: WaydroidConfig, runner=subprocess.run):
        self.cfg = cfg
        self._run = runner
        self._started_at: float | None = None

    def start(self) -> None:
        """Start the container and load binder (on demand)."""
        self._run(["modprobe", BINDER_MODULE], check=True)
        self._run(["waydroid", "session", "start"], check=True)
        self._started_at = time.monotonic()

    def stop(self) -> None:
        """Fully stop the container and unload binder."""
        self._run(["waydroid", "session", "stop"], check=True)
        self._run(["rmmod", BINDER_MODULE], check=False)
        self._started_at = None

    def idle_freeze(self) -> bool:
        """Freeze the container if it has been idle past the delay.

        Returns True if a freeze was performed.
        """
        if not self.cfg.auto_freeze or self._started_at is None:
            return False
        idle = time.monotonic() - self._started_at
        if idle < self.cfg.freeze_delay_s:
            return False
        self._run(["lxc-freeze", "-n", "waydroid"], check=False)
        return True

    def resume(self) -> None:
        self._run(["lxc-unfreeze", "-n", "waydroid"], check=False)
        self._started_at = time.monotonic()
