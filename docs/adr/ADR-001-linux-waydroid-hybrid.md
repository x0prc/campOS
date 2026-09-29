# ADR-001: Linux + Waydroid hybrid instead of an AOSP fork

## Status

Accepted

## Context

campOS must give users hard privacy controls (kill switches, default-deny
networking, transparent audit logs) while still running the Android apps
people expect on a TV. The two candidate bases were:

- An AOSP/Android TV fork (GrapheneOS-style): great app compatibility, but
  privacy tooling must be built into the Android framework, the build system
  is heavy, and TV SoC vendor trees are poorly documented.
- A pure Linux stack: full control and hackability, but no Android apps.
- A Linux base with Android apps in a container (Waydroid): both, at the cost
  of container integration complexity.

## Decision

Build campOS on a **Linux base with Waydroid** providing Android app support.

## Alternatives Considered

- **AOSP fork** — best app compatibility, but worst maintainability for a
  small project; TV vendor kernels are a swamp; privacy features locked into
  Android internals.
- **Pure Linux (Kodi/Plasma only)** — simplest, but loses the Android app
  ecosystem entirely; too big a compromise for v1.

## Consequences

- Positive: privacy daemon is ordinary Linux code (nftables, udev,
  PipeWire) — auditable and testable; Android apps remain available.
- Positive: base OS footprint stays small; Android container only runs when
  needed.
- Negative: Waydroid carries GPU/binder integration risk (see ADR-002);
  Android apps see a container, not bare hardware.

## Trade-off

Maintainability and privacy-control clarity are prioritized over maximum
Android app fidelity.
