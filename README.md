# campOS

A privacy-focused operating system for smart TVs and TV boxes — the GrapheneOS
philosophy applied to the living room.

Built on a Linux base (Armbian/Debian) with Android app support via Waydroid,
designed for unlockable Amlogic-class TV boxes, with hard privacy guarantees:
default-deny networking, hardware/software microphone kill, and one-touch
factory reset.

## Why

Recent investigations (Gamers Nexus / Level1Techs, Sept 2026) showed LG TVs
scanning home networks, running ACR tracking, and capturing audio in standby —
and every major smart TV vendor does some version of this. campOS exists so
that a TV or box only talks to the network when *you* say so.

## Design goals

| Goal | How |
|------|-----|
| No telemetry, ever | Default-deny egress firewall (`nftables`); apps get network per-namespace, per-app opt-in |
| Hard mic kill | Software switch (PipeWire + udev) and, where hardware allows, GPIO-level cut |
| Hard reset | A/B rootfs slots + `campctl factory-reset` wipes userdata and rolls back |
| Runs on old hardware | Armbian mainline base on 1–2 GB RAM Amlogic boxes; Android container frozen when idle |
| Android apps | Waydroid with WayDroid-ATV images, started on demand |

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full picture and
[docs/adr/](docs/adr/) for the six decisions that shape the project.

```
┌──────────────────────────────────────────────────────┐
│ Plasma Bigscreen UI (Wayland, CEC remote)            │
├──────────────┬───────────────┬───────────────────────┤
│ campd        │ Waydroid      │ campctl CLI           │
│ • firewall   │ supervisor    │ • status              │
│ • mic kill    │ • on-demand   │ • factory-reset       │
│ • DNS block  │ • freeze idle │ • firewall/mic toggles│
│ • audit log  │               │                       │
├──────────────┴───────────────┴───────────────────────┤
│ Linux: Armbian base, pinned LTS kernel + binder      │
├──────────────────────────────────────────────────────┤
│ Amlogic S905X/X2/X3/X4 hardware                      │
└──────────────────────────────────────────────────────┘
```

## Repository layout

```
campd/       Privacy daemon + campctl CLI (Python)
build/       Image build scripts, Armbian overlay, userpatches
docs/        Architecture overview + ADRs + hardware matrix + lab procedures
fixtures/    Real-device telemetry domain lists (blocklist test data)
tools/       Capture-analysis scripts (telemetry extraction)
```

## Status

Pre-alpha. Currently: repo scaffold, `campd` skeleton with tests, build
harness for the Armbian-based image. See [ROADMAP.md](ROADMAP.md).

## License

GPL-3.0-or-later (see [LICENSE](LICENSE)).
