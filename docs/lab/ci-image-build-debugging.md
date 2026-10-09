# Lab: getting the first campOS image to build (7 real bugs)

Every bug below broke an image build end-to-end before the first
verified image existed (2026-10-09). Kept as a runbook: same symptoms,
same fixes.

| # | Symptom | Root cause | Fix |
| --- | --- | --- | --- |
| 1 | `bash: ... arithmetic syntax error` in Armbian scripts | macOS ships Bash 3.2; Armbian needs ≥5 | `brew install bash coreutils`; run builds with brew bash |
| 2 | kernel build dies in `pahole`/BTF | Docker VM has 3.8 GiB; BTF generation OOMs | `KERNEL_BTF=no` (build-image.sh) |
| 3 | kernel 6.18 built, Waydroid/binder risk | `BRANCH=current` ≠ ADR-002's 6.12 LTS | `BRANCH=oldlts` |
| 4 | `patch ... FAILED` (meson-aiu HDMI) | broken upstream patch vs 6.12.111 | disable patch in local clone; CI fresh clones didn't hit it (fixed upstream) |
| 5 | OOM-kill mid kernel build | Armbian default `-j12` (150% of 8 CPUs) vs 3.8 GiB VM | `export CPUTHREADS=2` (env is forwarded into docker) |
| 6 | `Failed to enable unit, unit campd.service does not exist` | Armbian mounts `$USERPATCHES_PATH/overlay`, not a sibling `build/overlay` | `git mv build/overlay build/userpatches/overlay` |
| 7 | chroot apt: `getaddrinfo ... Device or resource busy` for all sources, right after `Calling image customization script` | customize-image.sh pinned `/etc/resolv.conf` → 127.0.0.1 during build; Armbian runs more apt after the hook | pin at **boot** instead: `campd.service` `ExecStartPre` `rm -f` + write (rm first: image may ship a resolved stub symlink) |
| 8 | local image had **no campd** (empty `/tmp`, vanilla) while CI images were fine | Armbian force-sets `USERPATCHES_PATH=${SRC}/userpatches` in the docker path; our userpatches sat beside `armbian-build` and the container never mounted it | symlink `armbian-build/userpatches → ../userpatches` (both values resolve to our content) + stage campd into `userpatches/.campd-src` (only path the container mounts) |

## Verification method (no hardware needed)

You cannot mount ext4 images on macOS. Extract and inspect instead:

```bash
# partition 2 (rootfs) start/count from MBR, then:
dd if=IMG of=rootfs.img bs=512 skip=$START count=$COUNT
brew install e2fsprogs   # keg-only: /opt/homebrew/opt/e2fsprogs/sbin/debugfs
debugfs -R "stat /etc/systemd/system/campd.service" rootfs.img
debugfs -R "ls /etc/systemd/system/multi-user.target.wants" rootfs.img
debugfs -R "cat /etc/campd/campd.toml" rootfs.img
```

A campOS image must show: `campd.service` + `dnsmasq.service` symlinks in
`multi-user.target.wants`, `campctl` in `/usr/local/bin`, campd.toml with
the Quad9 upstream. CI logs must contain `campOS: installing base privacy
stack` under `Calling image customization script`.

## Notes

- CI (GitHub Actions, `PREFER_DOCKER=no` native) is the source of truth;
  local Docker Desktop on macOS is fragile (OOM, unexplained VM exits).
  Remember: the Armbian native switch is `PREFER_DOCKER=no`, **not**
  `DOCKER=no`.
- Don't edit Docker Desktop's `MemoryMiB`/`SwapMiB` in
  `settings-store.json` — values >4 GiB prevent the VM from booting.
- Armbian output lives in `output/logs/log-build-*.log` with section
  markers (`### customize_image.log`); the script's stdout is there, not
  necessarily in `build/build.log`.
- Never `docker ps -q | xargs docker kill` on this machine — it takes the
  lab stack (crAPI/postgres/mongodb/mailhog) down with it.
