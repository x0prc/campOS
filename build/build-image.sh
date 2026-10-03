#!/usr/bin/env bash
# Build the first campOS image: Armbian bookworm + campOS overlay.
#
# Usage:
#   ./build-image.sh [board]
#
# Defaults to aml-s9xx-box (Amlogic S905-S922X TV boxes), matching ADR-002.
# Armbian runs inside Docker by default; the overlay + campd are injected
# via userpatches (customize-image-host.sh stages campd, customize-image.sh
# installs both inside the chroot).
set -euo pipefail

BOARD="${1:-aml-s9xx-box}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARMBIAN_SRC="${ARMBIAN_SRC:-$HERE/armbian-build}"

if [[ ! -x "$ARMBIAN_SRC/compile.sh" ]]; then
    echo "error: armbian/build not found at $ARMBIAN_SRC" >&2
    echo "  git clone --depth=1 https://github.com/armbian/build.git $ARMBIAN_SRC" >&2
    exit 1
fi

echo "==> campOS image build"
echo "    board:      $BOARD"
echo "    armbian:    $ARMBIAN_SRC"
echo "    userpatches: $HERE/userpatches"

cd "$ARMBIAN_SRC"
# Docker VM has only 3.8 GiB; Armbian's default is -j12 (150% of 8 CPUs)
# which OOM-kills the kernel build. 2 jobs keeps peak RSS well under the VM.
export CPUTHREADS="${CPUTHREADS:-2}"
./compile.sh \
  BOARD="$BOARD" \
  BRANCH=oldlts \
  RELEASE=bookworm \
  BUILD_MINIMAL=yes \
  BUILD_DESKTOP=no \
  KERNEL_CONFIGURE=no \
  KERNEL_BTF=no \
  CLEAN_LEVEL=none \
  USERPATCHES_PATH="$HERE/userpatches"

echo "==> done; images in $ARMBIAN_SRC/output/images/"
