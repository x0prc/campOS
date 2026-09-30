#!/usr/bin/env bash
# Extract telemetry candidates from a packet capture of a stock device.
#
# Takes a pcap/pcapng captured on the LAN (see docs/lab/airtel-telemetry-capture.md)
# and prints sorted unique destinations in blocklist format:
#   - DNS query names (port 53)
#   - TLS SNI hostnames (visible in plaintext ClientHello — catches DoT users)
#
# Usage: ./extract-telemetry.sh capture.pcapng
# Requires: tshark (Wireshark CLI)
set -euo pipefail

PCAP="${1:?usage: $0 capture.pcap}"

command -v tshark >/dev/null || { echo "tshark not found" >&2; exit 1; }

{
    # DNS queries
    tshark -r "$PCAP" -Y "dns.flags.response == 0" \
        -T fields -e dns.qry.name 2>/dev/null | tr ',' '\n'
    # TLS SNI (pre-ECH ClientHello)
    tshark -r "$PCAP" -Y "tls.handshake.extensions_server_name" \
        -T fields -e tls.handshake.extensions_server_name 2>/dev/null | tr ',' '\n'
} | sed 's/\.$//' | tr '[:upper:]' '[:lower:]' | \
    grep -E '^[a-z0-9-]+(\.[a-z0-9-]+)+$' | sort -u
