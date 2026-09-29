from pathlib import Path

from campd.config import CampConfig, load_config


def test_defaults_when_file_missing(tmp_path: Path):
    cfg = load_config(tmp_path / "nope.toml")
    assert isinstance(cfg, CampConfig)
    assert cfg.firewall.default_deny is True
    assert cfg.mic.kill_switch is False
    assert cfg.dns.listen == "127.0.0.1"
    assert cfg.waydroid.auto_freeze is True


def test_load_partial_config(tmp_path: Path):
    path = tmp_path / "campd.toml"
    path.write_text(
        """
[firewall]
default_deny = true
allowed_outbound_uids = [101, 999]

[mic]
kill_switch = true

[dns]
blocklists = ["https://example.com/list.txt"]
"""
    )
    cfg = load_config(path)
    assert cfg.firewall.allowed_outbound_uids == [101, 999]
    assert cfg.mic.kill_switch is True
    assert cfg.dns.blocklists == ["https://example.com/list.txt"]
    assert cfg.waydroid.auto_freeze is True  # untouched section -> default
