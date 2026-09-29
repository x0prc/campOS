# ADR-005: Default-deny egress firewall as the privacy backbone

## Status

Accepted

## Context

Privacy TV OSes typically rely on blocklists (ads/trackers domains) or
per-app toggles. Blocklists fail open by definition — a new tracker domain
leaks until the list is updated. The LG controversy showed data going to
vendor infrastructure that no blocklist anticipated. campOS needs a guarantee
that holds even for unknown/unexpected destinations.

## Decision

Enforce **default-deny egress** at the OS level: the `nftables` output chain
policy is `drop`; only explicitly allowed traffic passes (loopback,
DHCP, DNS to the local resolver, established sessions, plus per-app /
per-destination grants). Denials are logged to an audit trail. DNS goes
through a local resolver with blocklists as defense-in-depth, not as the
primary control.

## Alternatives Considered

- **Blocklist-only (Pi-hole style)** — easy, but fails open; can't stop
  direct-IP beacons or new domains.
- **Per-app network toggles only (GrapheneOS-style)** — great UX, but a
  single "allow" still permits that app to phone anywhere; useful as a
  grant layer *on top of* default-deny, not instead of it.
- **VPN-to-filter model** — adds a trusted third-party hop or self-hosted
  complexity.

## Consequences

- Positive: hard guarantee — nothing leaves without a rule; matches the
  project's "Graphene for TVs" promise.
- Positive: audit log of denials doubles as a transparency feature.
- Negative: aggressive defaults can break app updates/CDNs until users grant
  access; requires careful baseline rules (NTP, DHCP, OTA endpoints) and a
  good grant UX.
- Negative: per-namespace accounting for the Waydroid container needs
  cgroup/mark tagging in campd.

## Trade-off

Strictness and a verifiable guarantee are prioritized over "it just works"
networking; the grant UX must make granting easy to compensate.
