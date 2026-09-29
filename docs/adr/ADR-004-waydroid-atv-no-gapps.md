# ADR-004: WayDroid-ATV images, no GApps

## Status

Accepted

## Context

Android apps on campOS run inside Waydroid. Upstream Waydroid ships a
phone-style LineageOS image; campOS needs a TV-flavored image (leanback
launcher, remote-friendly apps) and must not ship Google Play Services —
Play Services would be the single largest telemetry surface in the system,
defeating the project's purpose.

## Decision

Use community **WayDroid-ATV** builds (Android TV Lineage images for
Waydroid) as the container image, **without GApps**. Users sideload APKs or
use an open app store; microG is available as an explicit opt-in for apps
that hard-require Google APIs.

## Alternatives Considered

- **Upstream Waydroid vanilla image** — phone UI on a TV; awkward with a
  remote.
- **GApps included** — best app compatibility, but imports Google telemetry
  and account plumbing; unacceptable for campOS's threat model.
- **microG by default** — closer to privacy-safe, but Google's
  device-attestation endpoints are still contacted; make it opt-in so the
  default is zero Google traffic.

## Consequences

- Positive: default state = no Google endpoints contacted, ever.
- Positive: TV-style UI works with a remote out of the box.
- Negative: some streaming/sideloaded apps that require Play Integrity won't
  work (accepted: HD DRM streaming is not a v1 requirement).
- Negative: sideloading is less convenient than an app store.

## Trade-off

Zero Google traffic by default is prioritized over app convenience.
