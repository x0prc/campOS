"""campctl — command-line interface to campd."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from . import __version__
from . import firewall as fw
from . import mic as micmod
from . import probe
from . import supervisor
from .config import load_config
from .dns import is_domain
from .reset import ResetError, current_system, factory_reset
from . import state as state_mod


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="campctl", description="campOS privacy control"
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="show enforced privacy status")

    fw_p = sub.add_parser("firewall", help="firewall operations")
    fw_sub = fw_p.add_subparsers(dest="fw_cmd", required=True)
    fw_sub.add_parser("show", help="render effective ruleset")
    fw_sub.add_parser("apply", help="apply ruleset (requires root)")
    for verb in ("allow", "deny"):
        g = fw_sub.add_parser(verb, help=f"{verb} a uid or domain grant")
        g.add_argument("kind", choices=["uid", "domain"])
        g.add_argument("value", help="numeric uid or domain name")

    mic_p = sub.add_parser("mic", help="microphone kill switch")
    mic_sub = mic_p.add_subparsers(dest="mic_cmd", required=True)
    mic_sub.add_parser("status", help="show mic kill state")
    mic_sub.add_parser("on", help="engage kill switch (mic off)")
    mic_sub.add_parser("off", help="disengage kill switch (mic on)")
    mic_sub.add_parser("sync", help="re-apply kill state from disk (boot)")

    dns_p = sub.add_parser("dns", help="local resolver + blocklists")
    dns_sub = dns_p.add_subparsers(dest="dns_cmd", required=True)
    dns_sub.add_parser("show", help="render dnsmasq drop-in config")
    dns_sub.add_parser("apply", help="write config and reload dnsmasq")
    dns_sub.add_parser(
        "fetch",
        help="download URL blocklists into cache, then apply (needs egress)",
    )

    audit_p = sub.add_parser("audit", help="denied-connection log")
    audit_sub = audit_p.add_subparsers(dest="audit_cmd", required=True)
    tail = audit_sub.add_parser("tail", help="show recent denied connections")
    tail.add_argument("--limit", type=int, default=20)
    ing = audit_sub.add_parser("ingest", help="pull journal -> audit log")
    ing.add_argument("--since", default="10 min ago")

    wd_p = sub.add_parser("waydroid", help="Android container")
    wd_sub = wd_p.add_subparsers(dest="wd_cmd", required=True)
    wd_sub.add_parser("start")
    wd_sub.add_parser("stop")

    fr = sub.add_parser("factory-reset", help="wipe data and roll back slot")
    fr.add_argument("--yes", action="store_true",
                    help="confirm destructive reset")

    args = parser.parse_args(argv)
    cfg = load_config()
    st = state_mod.load_state()

    dispatch = {
        "status": lambda: _status(cfg, st),
        "firewall": lambda: _firewall(args, cfg, st),
        "mic": lambda: _mic(args, cfg, st),
        "dns": lambda: _dns(args, cfg),
        "audit": lambda: _audit(args),
        "waydroid": lambda: _waydroid(args, cfg),
        "factory-reset": lambda: _factory_reset(args),
    }
    return dispatch[args.cmd]()


def _status(cfg, st) -> int:
    eff_fw = state_mod.effective_firewall(cfg, st)
    eff_mic = state_mod.effective_mic(cfg, st)
    state = {
        "system": current_system(),
        "firewall_default_deny": eff_fw.default_deny,
        "firewall": probe.probe_firewall(),
        "mic_kill": eff_mic.kill_switch,
        "mic_rules": probe.probe_mic_rules(),
        "dns": probe.probe_dns(),
        "waydroid": probe.probe_waydroid(),
        "granted_uids": eff_fw.allowed_outbound_uids,
        "granted_domains": eff_fw.allowed_domains,
    }
    print(json.dumps(state, indent=2))
    return 0


def _firewall(args, cfg, st) -> int:
    if args.fw_cmd in ("allow", "deny"):
        return _grant(args, st)

    eff = state_mod.effective_firewall(cfg, st)
    ruleset = fw.render_ruleset(eff, cfg.dns.listen, cfg.dns.port)
    if args.fw_cmd == "show":
        print(ruleset, end="")
        return 0
    try:
        fw.apply(ruleset)
    except FileNotFoundError:
        print("error: nftables not available on this system",
              file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"error: nft failed ({exc}) — root required?",
              file=sys.stderr)
        return 1
    added = fw.add_domain_elements(eff.allowed_domains)
    print(f"firewall applied ({added} domain elements resolved)")
    return 0


def _grant(args, st) -> int:
    if args.kind == "uid":
        try:
            value: int | str = int(args.value)
        except ValueError:
            print(f"error: uid must be numeric, got {args.value!r}",
                  file=sys.stderr)
            return 1
        grant_list: list = st.granted_uids
    else:
        if not is_domain(args.value):
            print(f"error: not a valid domain: {args.value!r}",
                  file=sys.stderr)
            return 1
        value = args.value.lower().rstrip(".")
        grant_list = st.granted_domains

    if args.fw_cmd == "allow":
        if value not in grant_list:
            grant_list.append(value)
        verb = "granted"
    else:
        if value in grant_list:
            grant_list.remove(value)
        verb = "revoked"

    state_mod.save_state(st)
    print(f"{value} {verb} — run 'campctl firewall apply' to enforce")
    return 0


def _mic(args, cfg, st) -> int:
    if args.mic_cmd == "status":
        engaged = state_mod.effective_mic(cfg, st).kill_switch
        print("mic kill: " + ("ENGAGED (mic off)" if engaged
                              else "released (mic on)"))
        return 0

    if args.mic_cmd in ("on", "off"):
        st.mic_kill = args.mic_cmd == "on"
        state_mod.save_state(st)

    eff_mic = state_mod.effective_mic(cfg, st)
    reloaded = micmod.apply(eff_mic)
    engaged = eff_mic.kill_switch
    if args.mic_cmd == "sync":
        print("mic state synced from disk")
    else:
        print("mic kill " + ("engaged" if engaged else "released"))
    if not reloaded:
        print("note: udevadm unavailable — rules written for next boot",
              file=sys.stderr)
    return 0


def _dns(args, cfg) -> int:
    from . import dns as dnsmod

    if args.dns_cmd == "show":
        domains = dnsmod.collect_domains(cfg.dns.blocklists)
        print(dnsmod.render_dnsmasq(cfg.dns, domains), end="")
        return 0
    if args.dns_cmd == "fetch":
        for source, status in dnsmod.fetch_blocklists(cfg.dns.blocklists):
            print(f"{status}: {source}")
    try:
        dnsmod.apply(cfg.dns)
    except (FileNotFoundError, OSError) as exc:
        print(f"error: could not apply DNS config ({exc})", file=sys.stderr)
        return 1
    print("dnsmasq config written and reloaded")
    return 0


def _audit(args) -> int:
    from . import audit as auditmod

    if args.audit_cmd == "ingest":
        count = auditmod.ingest_journal(since=args.since)
        if count < 0:
            print("error: journal unavailable on this system",
                  file=sys.stderr)
            return 1
        print(f"{count} new entries ingested")
        return 0
    entries = auditmod.tail_denied(limit=args.limit)
    if not entries:
        print("audit log empty")
        return 0
    for entry in entries:
        print(auditmod.format_entry(entry))
    return 0


def _waydroid(args, cfg) -> int:
    sup = supervisor.Supervisor(cfg.waydroid)
    if args.wd_cmd == "start":
        sup.start()
        print("waydroid started")
    else:
        sup.stop()
        print("waydroid stopped")
    return 0


def _factory_reset(args) -> int:
    try:
        factory_reset(confirm=args.yes)
    except ResetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("userdata wiped; boot slot flipped — reboot to complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
