"""Factory reset and A/B slot management.

Slot switching shells out to ``camp-bootctl`` (a small helper installed by
the image build); wiping /data is a direct rm once confirmed. All mutating
operations require explicit confirmation.
"""

from __future__ import annotations

import subprocess

DATA_PATH = "/data"


class ResetError(RuntimeError):
    pass


def factory_reset(confirm: bool, *, data_path: str = DATA_PATH,
                  runner=subprocess.run) -> None:
    """Wipe userdata (incl. Waydroid) and roll back to the other slot."""
    if not confirm:
        raise ResetError(
            "factory reset wipes all data; pass confirm=True to proceed"
        )
    runner(["camp-bootctl", "set-next-slot", "other"], check=True)
    runner(["rm", "-rf", f"{data_path}/*"], check=True)
    runner(["mkdir", "-p", data_path], check=True)


def active_slot(runner=subprocess.run) -> str:
    result = runner(
        ["camp-bootctl", "active-slot"], check=True, capture_output=True
    )
    return result.stdout.decode().strip()


def current_system() -> dict[str, str]:
    """OS identity for status output."""
    info = {"name": "campOS", "slot": "unknown"}
    try:
        info["slot"] = active_slot()
    except Exception:
        pass
    return info
