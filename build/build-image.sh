#!/usr/bin/env bash
# Build a campOS image from an Armbian source checkout.
#
# Usage:
#   ARMBIAN_SRC=/path/to/armbian/build ./build-image.sh [board]
#
# Defaults to the aml-s9xx-box board (Amlogic S905-S922X TV boxes).
# The campOS overlay (build/overlay) is copied into the image rootfs via
# the userpatches hook in userpatches/customize-image.sh.
set -euo pipefail

BOARD="${1:-aml-s9xx-box}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARMBIAN_SRC="${ARMBIAN_SRC:?set ARMBIAN_SRC to an armbian/build checkout}"

OVERLAY="$HERE/overlay"
USERPATCHES="$HERE/userpatches"

echo "==> campOS image build"
echo "    board:      $BOARD"
echo "    armbian:    $ARMBIAN_SRC"
echo "    overlay:    $OVERLAY"

# 1. Stage the campd Python package for installation into the image.
STAGE="$HERE/output/stage"
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -R "$HERE/../campd" "$STAGE/campd"
rm -rf "$STAGE/campd/.pytest_cache" "$STAGE/campd/**/__pycache__" || true

# 2. Run the Armbian build with our userpatches (copies overlay + campd).
cd "$ARMBIAN_SRC"
./compile.sh \
  BOARD="$BOARD" \
  BUILD_MINIMAL=no \
  BUILD_DESKTOP=no \
  KERNEL_CONFIGURE=yes \
  USERPATCHES_PATH="$USERPATCHES" \
  RELEASE=bookworm

echo "==> done; images in $ARMBIAN_SRC/output/images/"
