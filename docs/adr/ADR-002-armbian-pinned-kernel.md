# ADR-002: Armbian base with pinned LTS kernel

## Status

Accepted

## Context

The OS must boot on cheap Amlogic TV boxes (S905–S922X) whose vendor
bootloaders are locked but which happily boot mainline Linux from SD/USB via
the "toothpick" recovery button. It must also run Waydroid, which depends on
the `binder_linux` kernel module and has a history of breaking on brand-new
kernels (Rust-binder regressions in 6.18/7.0 caused system-wide crashes).

## Decision

Use **Armbian** (`aml-s9xx-box` board family, Debian userland) as the base,
**pinning a known-good LTS kernel** (6.12) with `binder_linux` built as a
module.

## Alternatives Considered

- **Buildroot/Yocto** — smallest images, but no package ecosystem; a solo
  maintainer would drown in rebuilds.
- **postmarketOS (Alpine)** — clean, but smaller package set and thinner
  Amlogic box coverage than Armbian.
- **Rolling kernel** — gets driver fixes faster, but Waydroid/binder
  breakage history makes this an availability risk.

## Consequences

- Positive: Armbian already boots mainline on the target SoCs without
  touching vendor u-boot (no brick risk); Debian packages for everything else.
- Positive: pinned kernel = reproducible Waydroid behavior.
- Negative: older kernel means waiting for some driver fixes; must
  periodically re-evaluate the pin.

## Trade-off

Reproducibility and low-risk installs are prioritized over being on the
newest kernel.
