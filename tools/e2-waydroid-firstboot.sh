#!/usr/bin/env bash
# campOS E2 — Waydroid first-boot experiment.
#
# Runs ON the campOS box (SSH or serial), as root. Verifies the pieces
# Waydroid needs (binder, lxc, networking under campd's firewall), then
# optionally installs and boots a WayDroid-ATV VANILLA container per
# ADR-004 (no GApps).
#
# Usage:
#   e2-waydroid-firstboot.sh              # preflight checks only
#   e2-waydroid-firstboot.sh --install    # check + install + init + start
#   e2-waydroid-firstboot.sh --report F   # append results to report file
#
# Exit code: 0 = all checks passed, 1 = at least one failure.
set -uo pipefail

DO_INSTALL=0
REPORT=""
while [[ $# -gt 0 ]]; do
	case "$1" in
		--install) DO_INSTALL=1; shift ;;
		--report) REPORT="$2"; shift 2 ;;
		*) echo "unknown arg: $1" >&2; exit 2 ;;
	esac
done

PASS=0 FAIL=0
note() { # level message
	local lvl="$1"; shift
	case "$lvl" in
		ok)   PASS=$((PASS + 1)); echo "[ ok ] $*" ;;
		fail) FAIL=$((FAIL + 1)); echo "[FAIL] $*" ;;
		info) echo "[ .. ] $*" ;;
	esac
	[[ -n "$REPORT" ]] && printf '%s\t%s\t%s\n' "$(date -u +%FT%TZ)" "$lvl" "$*" >>"$REPORT"
	return 0
}

# --- preflight ---------------------------------------------------------------

if [[ $(uname -m) != aarch64 ]]; then
	note info "arch is $(uname -m), not aarch64 — fine for bench, not for ship"
fi

if [[ $EUID -ne 0 ]]; then
	note fail "must run as root (sudo)"
else
	note ok "running as root"
fi

command -v campctl >/dev/null && note ok "campctl present" \
	|| note fail "campctl missing — is this a campOS image?"

command -v nft >/dev/null && note ok "nftables present" \
	|| note fail "nft missing"

command -v dnsmasq >/dev/null && note ok "dnsmasq present" \
	|| note fail "dnsmasq missing"

# Kernel binder support (ADR-002: LTS 6.12 + binder). Built-in or module.
CFG=""
if [[ -r /proc/config.gz ]]; then
	CFG="$(zcat /proc/config.gz)"
elif [[ -r "/boot/config-$(uname -r)" ]]; then
	CFG="$(cat "/boot/config-$(uname -r)")"
fi
if [[ -z "$CFG" ]]; then
	note info "kernel config not readable (no IKCONFIG) — checking devices instead"
else
	grep -q '^CONFIG_ANDROID_BINDER_IPC=y\|^CONFIG_ANDROID_BINDER_IPC=m' <<<"$CFG" \
		&& note ok "CONFIG_ANDROID_BINDER_IPC set" \
		|| note fail "CONFIG_ANDROID_BINDER_IPC not set — waydroid cannot run"
	grep -q '^CONFIG_ANDROID_BINDERFS=y' <<<"$CFG" \
		&& note info "binderfs available (preferred device provider)"
	grep -q '^CONFIG_ANDROID_BINDER_IPC=y$' <<<"$CFG" \
		&& note info "binder is BUILT-IN (ADR-002 says module; acceptable, devices idle until used)"
fi

if [[ -e /dev/binder || -d /dev/binderfs ]]; then
	note ok "binder device node present"
else
	# binderfs can be mounted on demand
	if mkdir -p /dev/binderfs 2>/dev/null && mount -t binder binder /dev/binderfs 2>/dev/null; then
		note ok "binderfs mounted on demand"
	else
		note fail "no /dev/binder and binderfs mount failed"
	fi
fi

# campd firewall state — setup needs egress for root (apt + image downloads).
if nft list table inet campd >/dev/null 2>&1; then
	note ok "campd firewall table active"
	if campctl firewall show 2>/dev/null | grep -qE 'skuid (0|root)\b'; then
		note ok "root (uid 0) already granted egress"
	else
		note info "root not granted — granting uid 0 for setup (revoke later)"
		campctl firewall allow uid 0 && campctl firewall apply \
			&& note ok "granted uid 0 + applied" \
			|| note fail "could not grant uid 0 (campctl firewall allow uid 0)"
	fi
else
	note info "campd firewall table not active (early milestone state)"
fi

# Resolver sanity: /etc/resolv.conf must point at campd's dnsmasq (127.0.0.1)
if grep -q '^nameserver 127\.0\.0\.1' /etc/resolv.conf 2>/dev/null; then
	note ok "/etc/resolv.conf -> 127.0.0.1"
else
	note fail "/etc/resolv.conf not pinned to 127.0.0.1: $(head -1 /etc/resolv.conf 2>/dev/null)"
fi

# Two dnsmasq listeners must coexist later (127.0.0.1:53 campd + waydroid0)
ss -lunp 2>/dev/null | grep -q ':53 ' \
	&& note ok "something already listens on :53 (campd dnsmasq)" \
	|| note info "nothing on :53 yet — dnsmasq not running?"

df -P / | awk 'NR==2 {print int($4/1024/1024)}' | grep -qE '^[1-9][0-9]*$' \
	&& note ok "rootfs has free space" \
	|| note fail "rootfs full"
AVAIL_MB=$(df -P / | awk 'NR==2 {print int($4/1024)}')
[[ $AVAIL_MB -ge 4096 ]] && note ok "free space ${AVAIL_MB}MB >= 4GB" \
	|| note fail "need >= 4GB free for waydroid images (have ${AVAIL_MB}MB)"

# --- install (opt-in) --------------------------------------------------------

if [[ $DO_INSTALL -eq 1 ]]; then
	echo "== install phase =="

	if ! command -v waydroid >/dev/null; then
		note info "installing waydroid CLI from official repo"
		if curl -fsSL https://repo.waydroid.net | bash; then
			apt-get install -y waydroid lxc \
				&& note ok "waydroid + lxc installed" \
				|| note fail "apt install waydroid failed"
		else
			note fail "could not fetch https://repo.waydroid.net installer"
		fi
	else
		note ok "waydroid CLI already installed"
	fi

	# ADR-004: WayDroid-ATV, VANILLA (no GApps), no microG by default.
	if [[ ! -f /var/lib/waydroid/images/system.img ]]; then
		note info "initializing WayDroid-ATV VANILLA (OTA a16-tv)"
		waydroid init -f \
			-c https://waydroid-atv.github.io/ota/a16-tv/system \
			-v https://waydroid-atv.github.io/ota/a16-tv/vendor \
			-r lineage -s VANILLA \
			&& note ok "waydroid init (VANILLA ATV)" \
			|| note fail "waydroid init failed"
		waydroid upgrade && note ok "images downloaded" \
			|| note fail "waydroid upgrade (image download) failed"
	else
		note ok "waydroid images already present"
	fi

	systemctl enable --now waydroid-container 2>/dev/null
	systemctl is-active --quiet waydroid-container \
		&& note ok "waydroid-container active" \
		|| note fail "waydroid-container not active"

	note info "starting waydroid session (binder + lxc)"
	waydroid session start >/dev/null 2>&1
	sleep 3
	waydroid status 2>/dev/null | grep -qi 'Session:\s*RUNNING' \
		&& note ok "waydroid session RUNNING" \
		|| { waydroid session start; sleep 3; waydroid status | grep -qi 'RUNNING' \
			&& note ok "waydroid session RUNNING (2nd try)" \
			|| note fail "waydroid session not running: $(waydroid status 2>&1 | tr '\n' ' ')"; }

	# --- verification ---
	BOOTED=$(waydroid shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')
	[[ "$BOOTED" == "1" ]] && note ok "Android booted (sys.boot_completed=1)" \
		|| note fail "Android not booted (sys.boot_completed='$BOOTED')"

	REL=$(waydroid shell getprop ro.build.version.release 2>/dev/null | tr -d '\r')
	note info "Android version: ${REL:-unknown}"

	ip link show waydroid0 >/dev/null 2>&1 \
		&& note ok "waydroid0 interface up" \
		|| note fail "waydroid0 missing"

	# NAT egress from inside the container (FORWARD path, not campd output chain)
	waydroid shell ping -c1 -W3 1.1.1.1 >/dev/null 2>&1 \
		&& note ok "container egress (ping 1.1.1.1)" \
		|| note fail "container has no egress"

	# DNS inside container resolves via waydroid NAT
	waydroid shell getprop net.dns1 2>/dev/null | grep -q . \
		&& note info "container dns1: $(waydroid shell getprop net.dns1 2>/dev/null | tr -d '\r')" \
		|| note info "no net.dns1 prop (may use host resolv via lxc)"

	# coexistence: campd dnsmasq on 127.0.0.1:53 must still be alive
	systemctl is-active --quiet dnsmasq \
		&& note ok "campd dnsmasq still active alongside waydroid" \
		|| note fail "dnsmasq died after waydroid start (port conflict?)"

	# ADR-004 compliance: no GApps
	waydroid shell pm list packages 2>/dev/null | grep -q 'com.google.android.gms' \
		&& note fail "Play Services present — ADR-004 violated (GAPPS image?)" \
		|| note ok "no Play Services (ADR-004 clean)"
fi

# --- summary -----------------------------------------------------------------

echo "== E2 summary: ${PASS} ok, ${FAIL} failed =="
[[ $FAIL -eq 0 ]]
