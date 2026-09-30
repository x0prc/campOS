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
