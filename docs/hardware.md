# campOS hardware matrix

## Development / target hardware

| Tier | Device | SoC | Why | Status |
|------|--------|-----|-----|--------|
| **Tier 1 (P0)** | X96 Max Plus, H96 Max X3, Beelink equivalents | Amlogic **S905X3** | Mali-G31, mainline Linux mature, toothpick SD boot, 2–4 GB RAM | **Needed — buy used ~$10–20** |
| Tier 2 | S905X2 / S922X boxes (e.g. Beelink GT-King) | Amlogic S905X2/S922X | Mali-G31/G52, good mainline support | P4 device matrix |
| Debug kit | USB-UART adapter (FTDI/CH340, 3.3V) | — | Boot logs when HDMI is silent | **Needed ~$5** |
| P2 lab | USB microphone | — | Real target for mic kill-switch testing | Later |

## Owned devices — usability

| Device | SoC / OS | campOS target? | Useful as | Notes |
|--------|----------|----------------|-----------|-------|
| **Airtel Xstream Box** (HSW4026ATL / XStream_Smart_Box_001) | Broadcom BCM72604 / Android 9 (kernel 4.9) | ❌ No mainline Linux, no boot path (Broadcom STB + operator lock) | ✅ **Telemetry lab device**: capture stock Android TV/Airtel/Google phoning home → blocklist fixtures (`docs/lab/airtel-telemetry-capture.md`); debloat reference via ADB | 2 GB RAM, 8 GB storage; ADB over network works (Developer Options → USB debugging); Wi-Fi only |
| **Tata Play T52** ("Dolby T52", Humax-manufactured HEVC HD STB) | Proprietary DTH stack, CAS-locked | ❌ No boot path, no developer access, satellite-broadcast device | ❌ None (spare HDMI/CEC test output at best) | Conditional access (smartcard) lock; no known root or community effort |

## Explicit non-targets

| Hardware | Reason |
|----------|--------|
| LG / Samsung / Sony TVs (panel firmware) | Locked bootloaders, per-model exploit work — long-term P4+ tier only, not v1 |
| Amazon Fire TV sticks | RPMB-enforced boot chain, no public root (as of 2026) |
| Cable/satellite operator boxes generally | CAS lock, operator-signed firmware, no SoC docs |
| Broadcom STB SoCs (any) | No mainline Linux support |

## Install media recap

- campOS boots from **SD/USB via Amlogic toothpick mode** (vendor u-boot,
  zero brick risk) — see ADR-006.
- Only install to eMMC after the image is proven on your specific box.
