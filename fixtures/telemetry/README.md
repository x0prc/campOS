# Telemetry fixtures

Domain lists extracted from real stock-device captures, used as test data
for campd's DNS blocklist module and firewall assertions.

## Format

One domain per line, `#` comments allowed — same format `campd.dns`
consumes directly:

```
# captured from Airtel Xstream Box, 2026-xx-xx, 30 min idle+usage
metrics.example.com
logs.vendor.example
```

## Files

| File | Source |
|------|--------|
| `starter.txt` | Well-known Google/Android telemetry endpoints (public documentation, no capture needed) |
| `airtel-capture.txt` | Your capture — run `tools/extract-telemetry.sh`, filter, add (see `docs/lab/airtel-telemetry-capture.md`) |

## Using in tests

```python
from campd.dns import collect_domains, render_dnsmasq

domains = collect_domains(["fixtures/telemetry/airtel-capture.txt"])
assert "some.tracker.example" in domains
```

Rules:

- **Never commit pcaps** — only extracted domain names.
- Mark provenance in a header comment (device, date, capture conditions).
- Split "block" candidates from "allow" (CDN/update) candidates before
  committing; this file is for the *block* set only.
