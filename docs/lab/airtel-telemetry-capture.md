# Lab: capturing stock telemetry from the Airtel Xstream Box

The Airtel Xstream Box (HSW4026ATL, Broadcom BCM72604, Android 9) is a
lab device for campOS: it runs stock Android TV with Airtel + Google
telemetry. Capturing what it phones home to gives us:

- a real-world **blocklist fixture** for `campd` DNS tests
- **ground-truth destinations** to assert against in firewall tests
- a documented "before" for campOS's "after" (privacy comparison)

## What you need

- Airtel box + your dev machine on the **same LAN**
- Router where you can run `tcpdump`, **or** a mirrored/SPAN port, **or**
  Wireshark on a machine whose traffic you can see (easiest: temporarily
  point the box's gateway/DNS through your laptop, or capture on the router
  with libpcap)
- `tshark` installed on the machine that will run the extraction

## Capture procedure

1. **Note the box's IP** (router DHCP client list; host starts with `hsw4026atl`).
2. **Disable Private DNS on the box** so queries go over plain DNS for the
   capture window: *Settings → Network → Private DNS → Off*. (Re-enable after.)
   — if you can't find it, don't worry: the extraction script also reads
   **TLS SNI**, which catches DoT/HTTPS destinations anyway.
3. **Start a capture** on the LAN interface, filtering the box:

   ```bash
   tcpdump -i eth0 -w airtel-capture.pcap host <BOX_IP> and not port 22
   ```

   Or in Wireshark: `ip.addr == <BOX_IP>`, Save As → pcapng.
4. **Exercise the box for 15–30 minutes**: idle on the home screen, open a
   few apps, play a video, let it sit in standby 5 minutes. Standby behavior
   is exactly what we care about (the LG scandal pattern).
5. Stop the capture.

## Convert to a blocklist fixture

```bash
./tools/extract-telemetry.sh airtel-capture.pcap > fixtures/telemetry/airtel-capture.txt
```

Review the output: separate destinations into

| Category | campOS handling |
|----------|----------------|
| Telemetry / ads / ACR | blocklist fixture (below) |
| CDN / update endpoints you want to allow | firewall grant list (`allowed_domains`) |
| DNS/NTP infrastructure | baseline rules already allow |

Then move the blocked set into `fixtures/telemetry/` and reference it from
`campd/tests` (see `fixtures/telemetry/README.md`).

## Handling encrypted DNS

Android 9+ may use Private DNS (DoT to 8.8.8.8). The script's SNI pass
recovers hostnames from TLS handshakes regardless. If both are empty, the
capture likely missed the box's interface — verify with
`tcpdump -i <if> host <BOX_IP>` showing packets.

## Privacy note

Captures contain your home LAN's traffic metadata. Keep pcaps out of git
(`.gitignore` already excludes `*.pcap*`); only commit the extracted,
domain-only fixture.
