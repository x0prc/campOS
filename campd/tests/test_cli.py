import json

from campd.cli import main


def test_status_output(capsys, monkeypatch):
    monkeypatch.setattr("campd.cli.load_config", lambda: _cfg())
    assert main(["status"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["firewall_default_deny"] is True
    assert out["mic_kill"] is False


def test_firewall_show(capsys, monkeypatch):
    monkeypatch.setattr("campd.cli.load_config", lambda: _cfg())
    assert main(["firewall", "show"]) == 0
    assert "policy drop" in capsys.readouterr().out


def test_factory_reset_without_yes_fails(capsys, monkeypatch):
    monkeypatch.setattr("campd.cli.load_config", lambda: _cfg())
    assert main(["factory-reset"]) == 1
    assert "error:" in capsys.readouterr().err


def _cfg():
    from campd.config import CampConfig

    return CampConfig()
