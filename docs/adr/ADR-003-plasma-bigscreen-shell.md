# ADR-003: Plasma Bigscreen as the TV shell

## Status

Accepted

## Context

campOS needs a 10-foot interface: D-pad/CEC remote navigation, big text,
couch-distance layout, and a settings surface where privacy controls can
live. Options were building a custom Wayland shell (months of work), using
Kodi as the whole shell (media-centric, awkward for non-media apps), or
adopting Plasma Bigscreen.

## Decision

Use **Plasma Bigscreen** (KDE) as the presentation layer, extended with
campOS settings screens for firewall, mic kill, and reset.

## Alternatives Considered

- **Custom wlroots compositor + UI** — maximum control, but a multi-month
  detour before any user-visible progress; ongoing maintenance burden.
- **Kodi-only shell** — polished media experience, poor fit for settings,
  Android app launching, and general app management.
- **Plasma Bigscreen (chosen)** — actively maintained (ships in the Plasma
  6.7 release cycle), Wayland-native, CEC remote support, existing couch
  settings app (Kirigami), and we can contribute upstream.

## Consequences

- Positive: usable TV UI from day one; inherits KDE accessibility/i18n;
  upstream collaboration possible.
- Positive: settings extension model exists (Kirigami apps in the Bigscreen
  settings menu).
- Negative: Plasma is heavier than a minimal custom shell (mitigated by
  targeting 2 GB boxes; 1 GB is best-effort).
- Negative: UI polish is subject to upstream pacing.

## Trade-off

Time-to-working-product and maintainability are prioritized over a bespoke,
fully controlled UI.
