#!/usr/bin/env bash
# Armbian customize-image hook: runs INSIDE the image chroot.
# Args: $1=release $2=linuxfamily $3=board $4=build_desktop $5=arch
#
# - copies the campOS overlay (systemd unit, default config) from
#   Armbian's bind-mount at /tmp/overlay into /
# - installs the campd privacy daemon (staged at /tmp/campd by
#   customize-image-host.sh)
# - installs the privacy stack: nftables, dnsmasq, python3
# - points the system resolver at campd's local dnsmasq
set -euo pipefail

echo "campOS: installing base privacy stack"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
    python3 python3-pip nftables dnsmasq iproute2

echo "campOS: installing overlay (unit + config)"
if [ ! -d /tmp/overlay ]; then
    echo "campOS: FATAL - /tmp/overlay not mounted (check userpatches/overlay exists)" >&2
    exit 1
fi
cp -a /tmp/overlay/. /

echo "campOS: installing campd"
if [ ! -d /tmp/campd ]; then
    echo "campOS: FATAL - /tmp/campd not staged (customize-image-host.sh)" >&2
    exit 1
fi
python3 -m pip install --no-cache-dir --break-system-packages /tmp/campd \
    || python3 -m pip install --no-cache-dir /tmp/campd
rm -rf /tmp/campd

# Apps must use campd's local resolver; dnsmasq forwards upstream itself
# (no-resolv + server= lines in the drop-in). Stop DHCP from clobbering it.
echo "nameserver 127.0.0.1" > /etc/resolv.conf
mkdir -p /etc/NetworkManager/conf.d
cat > /etc/NetworkManager/conf.d/campos-dns.conf <<'EOF'
[main]
dns=none
EOF

echo "campOS: enabling services"
systemctl enable campd.service
systemctl enable dnsmasq.service
# fail-safe: dnsmasq must never expose a plain open resolver
systemctl disable nftables.service 2>/dev/null || true

# Trimmings for 1-2 GB TV boxes
systemctl disable bluetooth.service 2>/dev/null || true
systemctl disable ModemManager.service 2>/dev/null || true

echo "campOS overlay installed."
