#!/usr/bin/env bash
# Sourced by Armbian on the build host, before the overlay mount.
# Stages the campd package into the chroot at /tmp/campd so
# customize-image.sh can pip-install it. Keep this file shell-safe:
# it runs inside Armbian's shell with set -e active.

CAMPD_SRC="$(cd "$(dirname "${USERPATCHES_PATH}")/.." && pwd)/campd"

if [[ -d "${CAMPD_SRC}/campd" ]]; then
	rm -rf "${SDCARD}/tmp/campd"
	cp -R "${CAMPD_SRC}" "${SDCARD}/tmp/campd"
	find "${SDCARD}/tmp/campd" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find "${SDCARD}/tmp/campd" -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	echo "staged campd from ${CAMPD_SRC}" >&2
fi

return 0 2>/dev/null || true
