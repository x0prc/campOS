#!/usr/bin/env bash
# Sourced by Armbian on the build host, before the overlay mount.
# Stages the campd package into the chroot at /tmp/campd so
# customize-image.sh can pip-install it. Keep this file shell-safe:
# it runs inside Armbian's shell with set -e active.

# Resolve campd from whichever USERPATCHES_PATH Armbian ends up using:
# 1. explicit override
# 2. staged copy inside userpatches (build-image.sh rsyncs it there; this is
#    the only location visible to docker builds, which don't mount campd/)
# 3. sibling layout: <root>/build/userpatches -> <root>/campd (native CI)
if [[ -z "${CAMPD_SRC:-}" && -d "${USERPATCHES_PATH}/.campd-src/campd" ]]; then
	CAMPD_SRC="${USERPATCHES_PATH}/.campd-src"
fi
if [[ -z "${CAMPD_SRC:-}" ]]; then
	CAMPD_SRC="$(cd "$(dirname "${USERPATCHES_PATH}")/.." && pwd)/campd"
fi

if [[ ! -d "${CAMPD_SRC}/campd" ]]; then
	# Fail loudly NOW: a silent skip produces a "successful" image with no
	# campd (customize-image.sh would then hard-fail much later anyway).
	echo "campOS FATAL: campd source not found at ${CAMPD_SRC}" >&2
	return 1 2>/dev/null || exit 1
fi

rm -rf "${SDCARD}/tmp/campd"
cp -R "${CAMPD_SRC}" "${SDCARD}/tmp/campd"
find "${SDCARD}/tmp/campd" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "${SDCARD}/tmp/campd" -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
echo "staged campd from ${CAMPD_SRC}" >&2

return 0 2>/dev/null || true
