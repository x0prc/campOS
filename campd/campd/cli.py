"""campctl — command-line interface to campd."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .config import load_config
from . import firewall as fw
from . import mic as micmod
from . import supervisor
from .reset import ResetError, current_system, factory_reset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="campctl", description="campOS privacy control"
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="show privacy status")

    fw_p = sub.add_parser("firewall", help="firewall operations")
    fw_sub = fw_p.add_subparsers(dest="fw_cmd", required=True)
    fw_sub.add_parser("show", help="render current ruleset")
    fw_sub.add_parser("apply", help="apply ruleset (requires root)")

    mic_p = sub.add_parser("mic", help="microphone kill switch")
    mic_sub = mic_p.add_subparsers(dest="mic_cmd", required=True)
    mic_sub.add_parser("status", help="show mic kill state")
    mic_sub.add_parser("on", help="engage kill switch (mic off)")
    mic_sub.add_parser("off", help="disengage kill switch (mic on)")

    wd_p = sub.add_parser("waydroid", help="Android container")
    wd_sub = wd_p.add_subparsers(dest="wd_cmd", required=True)
    wd_sub.add_parser("start")
    wd_sub.add_parser("stop")

    dns_p = sub.add_parser("dns", help="local resolver + blocklists")
    dns_sub = dns_p.add_subparsers(dest="dns_cmd", required=True)
    dns_sub.add_parser("show", help="render dnsmasq drop-in config")
    dns_sub.add_parser("apply", help="write config and reload dnsmasq")

    fr = sub.add_parser("factory-reset", help="wipe data and roll back slot")
    fr.add_argument("--yes", action="store_true",
                    help="confirm destructive reset")

    args = parser.parse_args(argv)
    cfg = load_config()

    if args.cmd == "status":
        return _status(cfg)
    if args.cmd == "firewall":
        return _firewall(args, cfg)
    if args.cmd == "mic":
        return _mic(args, cfg)
    if args.cmd == "waydroid":
        return _waydroid(args, cfg)
    if args.cmd == "dns":
        return _dns(args, cfg)
    if args.cmd == "factory-reset":
        return _factory_reset(args)
    return 2


def _status(cfg) -> int:
    state = {
        "system": current_system(),
        "firewall_default_deny": cfg.firewall.default_deny,
        "mic_kill": cfg.mic.kill_switch,
        "dns_blocklists": len(cfg.dns.blocklists),
    }
    print(json.dumps(state, indent=2))
    return 0


def _firewall(args, cfg) -> int:
    ruleset = fw.render_ruleset(
        cfg.firewall, cfg.dns.listen, cfg.dns.port
    )
    if args.fw_cmd == "show":
        print(ruleset, end="")
        return 0
    fw.apply(ruleset)
    print("firewall applied")
    return 0


def _mic(args, cfg) -> int:
    if args.mic_cmd == "status":
        print("mic kill: " + ("ENGAGED (mic off)" if cfg.mic.kill_switch
                              else "released (mic on)"))
        return 0
    # on/off mutate persistent config; persistence handled by image layer
    engaged = args.mic_cmd == "on"
    cfg.mic.kill_switch = engaged
    if engaged:
        print(micmod.render_udev_rules(cfg.mic), end="")
    print("mic kill " + ("engaged" if engaged else "released"))
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


def _dns(args, cfg) -> int:
    from . import dns as dnsmod

    if args.dns_cmd == "show":
        domains = dnsmod.collect_domains(cfg.dns.blocklists)
        print(dnsmod.render_dnsmasq(cfg.dns, domains), end="")
        return 0
    dnsmod.apply(cfg.dns)
    print("dnsmasq config written and reloaded")
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
