#!/usr/bin/env bash
# Armbian customize-image hook: runs inside the image chroot during build.
# Installs the campOS overlay and the campd package.
set -euo pipefail

# Overlay files (systemd unit, default config) are copied in by the
# pre-build hook; ensure they land even if invoked standalone.
if [ -d /tmp/campos-overlay ]; then
    cp -a /tmp/campos-overlay/. /
    rm -rf /tmp/campos-overlay
fi

# Install campd (staged by build-image.sh at /tmp/campd).
if [ -d /tmp/campd ]; then
    python3 -m pip install --no-cache-dir /tmp/campd
fi

# Enable the campd service.
systemctl enable campd.service

# Trimmings for a 1-2 GB TV box.
systemctl disable bluetooth.service 2>/dev/null || true
systemctl disable ModemManager.service 2>/dev/null || true

echo "campOS overlay installed."
