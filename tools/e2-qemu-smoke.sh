#!/usr/bin/env bash
# campOS QEMU smoke boot — boots a campOS image's kernel + rootfs in
# qemu-system-aarch64 (virt machine, no DTB needed) and asserts that the
# privacy stack actually comes up at boot:
#
#   RESOLV   /etc/resolv.conf pinned to 127.0.0.1 (campd.service ExecStartPre)
#   CAMPD    campd.service active
#   DNSMASQ  dnsmasq.service active
#   FIREWALL nft table inet campd present
#   LISTEN   dnsmasq bound on :53
#   CAMPCTL  /usr/local/bin/campctl present
#
# Works on any campOS image; the tested image is never modified (a
# copy-on-write clone + extracted rootfs are used, injection happens there).
# A guest-side script is injected into the clone via debugfs and triggered
# with systemd.run= on the kernel cmdline; its results are printed to the
# serial console and parsed on the host.
#
# Usage: tools/e2-qemu-smoke.sh <image> [--fresh]
#   --fresh   rebuild the working clone (default: reuse if source unchanged)
set -euo pipefail

IMAGE="${1:-}"
FRESH="${2:-}"
[ -n "$IMAGE" ] || { echo "usage: $0 <image> [--fresh]" >&2; exit 2; }
[ -f "$IMAGE" ] || { echo "error: no such image: $IMAGE" >&2; exit 2; }

for tool in qemu-system-aarch64 mcopy mdir python3 gtimeout; do
	command -v "$tool" >/dev/null || { echo "error: missing $tool" >&2; exit 2; }
done
DEBUGFS="$(command -v debugfs || true)"
[ -n "$DEBUGFS" ] || {
	for c in /opt/homebrew/opt/e2fsprogs/sbin/debugfs /usr/local/opt/e2fsprogs/sbin/debugfs; do
		[ -x "$c" ] && DEBUGFS="$c" && break
	done
}
[ -n "$DEBUGFS" ] || { echo "error: debugfs not found (brew install e2fsprogs)" >&2; exit 2; }

WORK="${CAMPOS_QEMU_WORK:-${TMPDIR:-/tmp}/campos-qemu-smoke}"
mkdir -p "$WORK"
SRC_HASH="$(shasum -a 256 "$IMAGE" | cut -c1-16)"

# --- guest-side smoke script (POSIX sh, injected into rootfs) -------------
SMOKE_SH="$WORK/qemu-smoke.sh"
cat > "$SMOKE_SH" <<'EOF'
#!/bin/sh
exec >/dev/console 2>&1
echo "===SMOKE==="
i=0
while [ "$i" -lt 60 ]; do
	if systemctl is-active --quiet campd.service 2>/dev/null \
		&& systemctl is-active --quiet dnsmasq.service 2>/dev/null; then
		break
	fi
	sleep 1
	i=$((i + 1))
done
echo "RESOLV=$(head -n 1 /etc/resolv.conf 2>/dev/null)"
echo "CAMPD=$(systemctl is-active campd.service 2>&1)"
echo "DNSMASQ=$(systemctl is-active dnsmasq.service 2>&1)"
if nft list tables 2>/dev/null | grep -q "table inet campd"; then
	echo "FIREWALL=ok"
else
	echo "FIREWALL=missing"
fi
if ss -lntu 2>/dev/null | grep -q ":53 "; then
	echo "LISTEN=ok"
else
	echo "LISTEN=missing"
fi
if [ -x /usr/local/bin/campctl ]; then echo "CAMPCTL=yes"; else echo "CAMPCTL=no"; fi
echo "MULTIUSER=$(systemctl is-active multi-user.target 2>&1)"
echo "---JOBS---"
systemctl list-jobs --no-legend 2>/dev/null | head -15
echo "---FAILED---"
systemctl --failed --no-legend 2>/dev/null | head -10
echo "---ACTIVATING---"
systemctl list-units --state=activating --no-legend 2>/dev/null | head -10
echo "===SMOKE_END==="
systemctl --no-block poweroff 2>/dev/null || poweroff -f 2>/dev/null || true
sleep 5
EOF
chmod +x "$SMOKE_SH"

# --- working clone (APFS copy-on-write; source never modified) ------------
CLONE="$WORK/work.img"
STAMP="$WORK/source.hash"
if [ "$FRESH" = "--fresh" ] || [ ! -f "$CLONE" ] || [ "$(cat "$STAMP" 2>/dev/null)" != "$SRC_HASH" ]; then
	echo "* building working clone (fresh) ..."
	rm -f "$CLONE" "$WORK/rootfs.part2.img" "$WORK/injected.stamp"
	cp -c "$IMAGE" "$CLONE" 2>/dev/null || cp "$IMAGE" "$CLONE"
	echo "$SRC_HASH" > "$STAMP"
fi

# --- parse MBR partition table -------------------------------------------
eval "$(python3 - "$IMAGE" <<'PYEOF'
import struct, sys
with open(sys.argv[1], "rb") as f:
    mbr = f.read(512)
parts = []
for i in range(4):
    e = mbr[446 + 16 * i: 446 + 16 * (i + 1)]
    if e[4] == 0:
        continue
    start, size = struct.unpack_from("<II", e, 8)
    parts.append((e[4], start * 512, size * 512))
boot = parts[0]
root = parts[1] if len(parts) > 1 else parts[0]
print(f"P1_OFF={boot[1]}; P1_SIZE={boot[2]}; P2_OFF={root[1]}; P2_SIZE={root[2]}")
PYEOF
)"

# --- extract kernel + initrd from FAT boot partition ----------------------
KERNEL="$WORK/Image"
INITRD_GLOB="$WORK/initrd.img-*"
if [ ! -f "$KERNEL" ] || ! compgen -G "$INITRD_GLOB" >/dev/null; then
	echo "* extracting kernel/initrd from boot partition ..."
	mcopy -o -i "$IMAGE@@$P1_OFF" ::/Image "$KERNEL"
	mcopy -o -i "$IMAGE@@$P1_OFF" ::/initrd.img-* "$WORK/" 2>/dev/null || true
fi
INITRD=""
for f in $INITRD_GLOB; do [ -f "$f" ] && INITRD="$f" && break; done

# --- extract + inject smoke script into rootfs (once per clone) -----------
INJECT="$WORK/injected.stamp"
SMOKE_HASH="$(shasum -a 256 "$SMOKE_SH" | cut -c1-16)"
NEED_INJECT="$SRC_HASH:$SMOKE_HASH"
if [ ! -f "$INJECT" ] || [ "$(cat "$INJECT" 2>/dev/null)" != "$NEED_INJECT" ]; then
	echo "* extracting rootfs partition (2 GB) ..."
	dd if="$CLONE" of="$WORK/rootfs.part2.img" bs=1m \
		skip=$((P2_OFF / 1048576)) count=$((P2_SIZE / 1048576)) status=none
	echo "* injecting guest smoke script via debugfs ..."
	printf 'rm /usr/local/bin/qemu-smoke.sh\nwrite %s /usr/local/bin/qemu-smoke.sh\nsif /usr/local/bin/qemu-smoke.sh mode 0x81ed\n' \
		"$SMOKE_SH" > "$WORK/debugfs.cmds"
	"$DEBUGFS" -w -f "$WORK/debugfs.cmds" "$WORK/rootfs.part2.img" 2>"$WORK/debugfs.err"
	# verify the file actually landed (debugfs errors don't always say "error")
	"$DEBUGFS" -R "stat /usr/local/bin/qemu-smoke.sh" "$WORK/rootfs.part2.img" 2>/dev/null \
		| grep -q "^Inode:" || { echo "error: debugfs injection failed" >&2; cat "$WORK/debugfs.err" >&2; exit 1; }
	echo "* writing injected rootfs back into clone ..."
	dd if="$WORK/rootfs.part2.img" of="$CLONE" bs=1m \
		seek=$((P2_OFF / 1048576)) conv=notrunc status=none
	echo "$NEED_INJECT" > "$INJECT"
fi

# --- boot ------------------------------------------------------------------
SERIAL="$WORK/serial.log"
APPEND="root=/dev/vda2 rootwait rw rootflags=data=writeback console=ttyAMA0,115200n8 earlycon=pl011,0x9000000 net.ifnames=0 fsck.fix=yes fsck.repair=yes loglevel=4 systemd.run=/usr/local/bin/qemu-smoke.sh"

echo "* booting (timeout 300 s) ..."
set +e
gtimeout --foreground 300 qemu-system-aarch64 \
	-M virt -accel hvf -cpu host -smp 2 -m 1536 \
	-kernel "$KERNEL" \
	${INITRD:+-initrd "$INITRD"} \
	-append "$APPEND" \
	-drive "if=virtio,file=$CLONE,format=raw" \
	-display none -serial "file:$SERIAL" \
	-no-reboot 2>"$WORK/qemu.err"
QEMU_RC=$?
set -e

# --- parse assertions ------------------------------------------------------
echo "=== serial log: $SERIAL ==="
if [ ! -s "$SERIAL" ]; then
	echo "FAIL: no serial output (qemu rc=$QEMU_RC)"; cat "$WORK/qemu.err" >&2; exit 1
fi

FAIL=0
check() { # check <key> <want>
	local key="$1" want="$2" got
	got="$(grep "^$key=" "$SERIAL" | tail -1 | cut -d= -f2-)"
	if [ "$got" = "$want" ]; then
		echo "  ok   $key=$got"
	else
		echo "  FAIL $key want='$want' got='${got:-<missing>}'"
		FAIL=1
	fi
}
if ! grep -q "===SMOKE===" "$SERIAL" || ! grep -q "===SMOKE_END===" "$SERIAL"; then
	echo "  FAIL guest smoke script did not complete (qemu rc=$QEMU_RC)"
	grep -E "systemd|campd|Kernel panic|VFS" "$SERIAL" | tail -20
	FAIL=1
else
	check RESOLV   "nameserver 127.0.0.1"
	check CAMPD    "active"
	check DNSMASQ  "active"
	check FIREWALL "ok"
	check LISTEN   "ok"
	check CAMPCTL  "yes"
fi

if [ "$FAIL" = "0" ]; then
	echo "SMOKE PASS"
else
	echo "SMOKE FAIL (qemu rc=$QEMU_RC) — full log: $SERIAL"
fi
exit "$FAIL"
