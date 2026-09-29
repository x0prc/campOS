# ADR-006: Toothpick/SD install and recovery, A/B slots for updates

## Status

Accepted

## Context

Target boxes have locked vendor bootloaders, but Amlogic vendor u-boot
happily boots signed-looking boot scripts from SD/USB when the hidden reset
button is held ("toothpick mode"). This is a proven, zero-brick install path
(used by debian-on-amlogic and Armbian). For day-2 operations campOS needs
safe updates and a factory reset that always works, even when the OS is
broken.

## Decision

- **Install/recovery:** boot a campOS image from SD/USB via toothpick mode;
  install to eMMC from the live environment. Recovery = same removable-media
  boot (dual-slot aware).
- **Updates:** A/B rootfs slots; OTA writes the inactive slot, flips boot
  selection, keeps the old slot for rollback.
- **Factory reset:** `campctl factory-reset` (UI or recovery) wipes `/data`
  (including Waydroid userdata) and rolls back to the other slot if the
  current slot is unhealthy.

## Alternatives Considered

- **Chain-loaded U-Boot unlock** — enables multiboot but carries a small
  brick risk and modifies vendor boot env; deferred (documented as opt-in
  later).
- **A/B with dm-verity + signed images** — ideal end state, but signing
  infra and verity bring-up is P3+; start with slot safety only.
- **Single-slot + rsync backups** — rollback failure modes are worse than
  A/B.

## Consequences

- Positive: install and recovery never touch vendor bootloaders →
  effectively unbrickable; recovery works with zero functioning campOS.
- Positive: A/B gives atomic updates with rollback.
- Negative: doubles rootfs storage footprint (acceptable: images are small,
  eMMC ≥ 4 GB on all tier-1 boxes).
- Negative: `/data` wipe loses Android app data on factory reset (expected
  and desired for a "hard reset").

## Trade-off

Install safety and guaranteed recovery are prioritized over a fully
verified-boot supply chain, which comes later.
