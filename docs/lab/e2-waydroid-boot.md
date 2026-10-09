# Lab: E2 — Waydroid first boot on campOS

E2 answers one question: **can the campOS image boot a WayDroid-ATV
container (no GApps) with campd's privacy stack still enforced?** It is the
first test that exercises ADR-001 (Linux + Waydroid hybrid), ADR-002
(LTS kernel + binder), ADR-004 (ATV, no Play Services) and ADR-005
(default-deny egress) at the same time.

Run it on real hardware (Tier 1 box, see `docs/hardware.md`) with the
first campOS image flashed. A bench VM without binder works for the
preflight half only.

## What you need

- campOS image written to eMMC/SD of an S905X3-class box
- Box on LAN with DHCP; SSH in as root (or serial console)
- ~4 GB free on rootfs (Waydroid images), internet egress **through**
  campd's firewall (the script grants uid 0 for setup and tells you how
  to revoke it)

## Procedure

```bash
scp tools/e2-waydroid-firstboot.sh root@<box>:/tmp/
ssh root@<box>
chmod +x /tmp/e2-waydroid-firstboot.sh

/tmp/e2-waydroid-firstboot.sh                 # 1. preflight only
/tmp/e2-waydroid-firstboot.sh --install \
    --report /tmp/e2-report.tsv               # 2. full run, keeps a report
```

Preflight checks (no changes except the uid-0 grant, which is reversible):

| Check | Pass looks like |
| --- | --- |
| campctl / nft / dnsmasq present | campOS image, not vanilla Armbian |
| `CONFIG_ANDROID_BINDER_IPC` | `=y` or `=m` in kernel config |
| binder device | `/dev/binder` exists or binderfs mounts |
| campd firewall | `inet campd` table active; uid 0 granted for setup |
| resolver | `/etc/resolv.conf` → `nameserver 127.0.0.1` |
| :53 listener | campd's dnsmasq bound |
| free space | ≥ 4096 MB |

Install phase (ADR-004 pinned choices): waydroid CLI from the official
repo, then `waydroid init` against the **WayDroid-ATV OTA** with
`-s VANILLA` — Lineage TV image, **no GApps, no microG**.

## Expected results

- `waydroid status` → Session: RUNNING, Container: RUNNING
- `sys.boot_completed=1`, Android release reported (16.x on a16-tv)
- `waydroid0` up; container can ping out (FORWARD/NAT path — campd's
  output chain does not filter routed container traffic; that is a
  deliberate ADR-005 gap to revisit, see below)
- `dnsmasq` still active (its `bind-interfaces` 127.0.0.1:53 must not
  collide with Waydroid's dnsmasq on `waydroid0`)
- `pm list packages` has no `com.google.android.gms` (ADR-004 proof)
- `campctl status` still reports default-deny for host processes

## Failure triage

| Symptom | Likely cause | Next move |
| --- | --- | --- |
| `CONFIG_ANDROID_BINDER_IPC` missing | custom kernel lost Armbian's config | restore `config/kernel/linux-meson64-oldlts.config`, rebuild |
| binder device absent, binderfs mount fails | config =n | same as above |
| session won't start | lxc missing or binder denied | `apt install lxc`; `journalctl -u waydroid-container` |
| container has no egress | NAT/forwarding off, or nft forward policy | check `ip netns`/`iptables -t nat -L`; confirm no forward-chain drop |
| host egress blocked during setup | firewall active, uid 0 not granted | `campctl firewall allow uid 0 && campctl firewall apply` |
| `dnsmasq` dies at waydroid start | port collision | confirm campd drop-in uses `bind-interfaces` + `127.0.0.1` only |
| Play Services present | wrong image (`-s GAPPS`) | `waydroid init -f -s VANILLA`, wipe `/var/lib/waydroid` first |

## Notes to record (feeds ADR updates + ROADMAP P1)

- Android version + WayDroid-ATV release tag that worked
- binder is built-in (`=y`) on Armbian oldlts, while ADR-002/architecture
  text assumes a load-on-demand module — decide: keep `=y` (idle devices
  cost nothing) or carry a config fragment to make it `=m`
- whether container egress needs its own campd chain (today it bypasses
  the output chain via NAT — gap noted in architecture's Waydroid row)
- host uid grants needed for real use (keep `uid 0` revoked outside setup;
  day-2 flow is `campctl firewall allow domain …` per app)

## After the run

```bash
# revoke setup grant — host goes back to default-deny
campctl firewall deny uid 0 && campctl firewall apply
# optional: freeze the container instead of stopping (P1 supervisor does this)
waydroid session stop
```

Copy `/tmp/e2-report.tsv` and `journalctl -u campd -u waydroid-container
-b` excerpts into the lab notes when filing results.
