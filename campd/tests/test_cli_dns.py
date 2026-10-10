def test_dns_show_renders_config(capsys, monkeypatch, tmp_path):
    from campd.config import CampConfig, DnsConfig

    bl = tmp_path / "blocklist.txt"
    bl.write_text("tracker.example.com\n")
    cfg = CampConfig(dns=DnsConfig(blocklists=[str(bl)], listen="127.0.0.1"))
    monkeypatch.setattr("campd.cli.load_config", lambda: cfg)

    from campd.cli import main

    assert main(["dns", "show"]) == 0
    out = capsys.readouterr().out
    assert "listen-address=127.0.0.1" in out
    assert "address=/tracker.example.com/0.0.0.0" in out


def test_dns_fetch_prints_statuses_and_applies(capsys, monkeypatch):
    from campd.config import CampConfig, DnsConfig

    cfg = CampConfig(
        dns=DnsConfig(blocklists=["https://example.com/list.txt", "/etc/x.txt"])
    )
    monkeypatch.setattr("campd.cli.load_config", lambda: cfg)
    seen = {}
    monkeypatch.setattr(
        "campd.dns.fetch_blocklists",
        lambda sources, cache_dir=None, opener=None: seen.setdefault(
            "sources", [("https://example.com/list.txt", "cached (12 bytes)"),
                        ("/etc/x.txt", "local (not fetched)")]
        ),
    )
    monkeypatch.setattr("campd.dns.apply", lambda dns_cfg: seen.setdefault("applied", True))

    from campd.cli import main

    assert main(["dns", "fetch"]) == 0
    out = capsys.readouterr().out
    assert "cached (12 bytes): https://example.com/list.txt" in out
    assert "local (not fetched): /etc/x.txt" in out
    assert seen.get("applied") is True
