"""camp-bootctl — A/B slot management for campOS (see ADR-006).

Slots are extlinux entries labeled ``camp-a`` / ``camp-b``; the active slot
is the one the running kernel was booted from. Detection order:

1. ``camp.slot=`` on the kernel command line (authoritative, once images
   ship it)
2. LABEL of the mounted root partition (``blkid`` via ``findmnt``)
3. the ``DEFAULT`` entry in extlinux.conf (what *will* boot next)

``set-next-slot`` rewrites the extlinux ``DEFAULT`` line — the A/B flip
used by factory reset and OTA rollback. On single-slot images (no
``camp-a``/``camp-b`` entries) commands fail with a clear error instead of
silently corrupting the boot config.

Path overrides for tests: CAMPD_CMDLINE, CAMPD_EXTLINUX.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SLOT_A = "camp-a"
SLOT_B = "camp-b"
_CMDLINE = re.compile(r"\bcamp\.slot=([ab])\b")
_LABEL = re.compile(r"^\s*LABEL\s+(camp-[ab])\s*$", re.MULTILINE)
_DEFAULT = re.compile(r"^\s*DEFAULT\s+(\S+)\s*$", re.MULTILINE)


class BootctlError(RuntimeError):
    pass


def _cmdline_path() -> Path:
    return Path(os.environ.get("CAMPD_CMDLINE", "/proc/cmdline"))


def _extlinux_path() -> Path:
    return Path(os.environ.get("CAMPD_EXTLINUX",
                               "/boot/extlinux/extlinux.conf"))


def _read_cmdline_slot() -> str | None:
    path = _cmdline_path()
    if not path.exists():
        return None
    match = _CMDLINE.search(path.read_text())
    return match.group(1) if match else None


def _read_root_label(runner=subprocess.run) -> str | None:
    try:
        src = runner(["findmnt", "-n", "-o", "SOURCE", "/"],
                     capture_output=True, check=True)
        device = src.stdout.decode().strip()
        label = runner(["blkid", "-s", "LABEL", "-o", "value", device],
                       capture_output=True, check=False)
        return label.stdout.decode().strip() or None
    except (FileNotFoundError, OSError, subprocess.CalledProcessError):
        return None


def active_slot(*, conf_path: Path | None = None,
                runner=subprocess.run) -> str:
    """Return 'a' or 'b' for the slot the current system booted from."""
    slot = _read_cmdline_slot()
    if slot:
        return slot
    label = _read_root_label(runner=runner)
    if label in (SLOT_A, SLOT_B):
        return label[-1]
    # Fall back: default entry counts only if it is a real slot label.
    info = slots_info(conf_path=conf_path)
    if info["default"] in (SLOT_A, SLOT_B):
        return info["default"][-1]
    raise BootctlError("cannot determine active slot (no camp.slot= on "
                       "cmdline, no camp-a/camp-b root label, no A/B DEFAULT)")


def slots_info(*, conf_path: Path | None = None) -> dict:
    """Parse extlinux.conf for slot entries and the DEFAULT target."""
    conf_path = conf_path or _extlinux_path()
    info = {
        "conf": str(conf_path),
        "entries": [],
        "default": None,
        "ab": False,
        "exists": conf_path.exists(),
    }
    if not conf_path.exists():
        return info
    text = conf_path.read_text()
    info["entries"] = sorted(set(_LABEL.findall(text)))
    default = _DEFAULT.search(text)
    info["default"] = default.group(1) if default else None
    info["ab"] = SLOT_A in info["entries"] and SLOT_B in info["entries"]
    return info


def set_next_slot(target: str, *, conf_path: Path | None = None,
                  runner=subprocess.run) -> str:
    """Point extlinux DEFAULT at target slot ('a', 'b', or 'other').

    Returns the slot now set as default. Raises BootctlError if the image
    has no A/B entries or the target entry is missing.
    """
    conf_path = conf_path or _extlinux_path()
    info = slots_info(conf_path=conf_path)
    if not info["exists"]:
        raise BootctlError(f"extlinux.conf not found: {conf_path}")
    if not info["ab"]:
        raise BootctlError(
            f"no A/B entries ({SLOT_A}/{SLOT_B}) in {conf_path} — "
            "single-slot image, refusing to touch boot config"
        )

    if target == "other":
        target = "b" if active_slot(conf_path=conf_path,
                                    runner=runner) == "a" else "a"
    if target not in ("a", "b"):
        raise BootctlError(f"invalid target: {target!r}")
    entry = SLOT_A if target == "a" else SLOT_B
    if entry not in info["entries"]:
        raise BootctlError(f"entry {entry} missing from {conf_path}")

    text = conf_path.read_text()
    if not _DEFAULT.search(text):
        raise BootctlError(f"no DEFAULT line in {conf_path}")
    new_text = _DEFAULT.sub(f"DEFAULT {entry}", text, count=1)

    shutil.copy2(conf_path, conf_path.with_suffix(conf_path.suffix + ".bak"))
    tmp = conf_path.with_suffix(conf_path.suffix + ".tmp")
    tmp.write_text(new_text)
    os.replace(tmp, conf_path)
    return entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="camp-bootctl", description="campOS A/B slot management"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("active-slot", help="print the booted slot (a|b)")
    sub.add_parser("slots", help="show slot entries and boot default")
    flip = sub.add_parser("set-next-slot",
                          help="set extlinux DEFAULT for next boot")
    flip.add_argument("target", choices=["a", "b", "other"])

    args = parser.parse_args(argv)
    try:
        if args.cmd == "active-slot":
            print(active_slot())
        elif args.cmd == "slots":
            info = slots_info()
            print(f"conf:     {info['conf']}")
            print(f"entries:  {', '.join(info['entries']) or 'none'}")
            print(f"default:  {info['default'] or 'none'}")
            print(f"a/b:      {'yes' if info['ab'] else 'no (single slot)'}")
            print(f"active:   {active_slot() if info['entries'] else '?'}")
        else:
            entry = set_next_slot(args.target)
            print(f"next boot: {entry}")
    except BootctlError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
