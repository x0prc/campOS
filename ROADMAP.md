# Roadmap

## P0 — Proof (current)
- [x] Repo scaffold, ADRs, build harness
- [ ] Armbian + Plasma Bigscreen boots on one S905X3 box
- [ ] CEC remote navigates the UI

## P1 — Android apps
- [ ] WayDroid-ATV image integrated, starts on demand
- [ ] Android app drawer in the launcher
- [ ] Container freezes on exit; binder module loaded only while running

## P2 — Privacy core
- [ ] `campd` default-deny firewall enforced at boot
- [ ] Mic kill switch (PipeWire + udev), wired into settings UI
- [ ] Local DNS resolver with blocklists on by default
- [ ] Connection audit log surfaced in settings

## P3 — Resilience
- [ ] A/B rootfs slots with OTA updates
- [ ] Recovery boot from removable media
- [ ] Factory reset from UI and `campctl`

## P4 — Scale
- [ ] Device matrix (X96 Mini, Beelink, ...)
- [ ] One-shot installer image
- [ ] Documentation + release process
