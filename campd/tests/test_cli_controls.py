import json

import pytest

from campd.cli import main
from campd.state import load_state


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("CAMPD_STATE_PATH", str(tmp_path / "state.json"))
    return tmp_path / "state.json"


@pytest.fixture
def cli(monkeypatch):
    """Load config without side-effectful applies (state tests only)."""
    from campd.config import CampConfig

    monkeypatch.setattr("campd.cli.load_config", lambda: CampConfig())
    monkeypatch.setattr("campd.mic.apply", lambda cfg, **kw: True)
    return CampConfig


def test_mic_on_persists_and_status_reflects(isolated_state, capsys, cli):
    assert main(["mic", "on"]) == 0
    assert load_state(isolated_state).mic_kill is True

    assert main(["mic", "status"]) == 0
    assert "ENGAGED" in capsys.readouterr().out

    assert main(["mic", "off"]) == 0
    assert load_state(isolated_state).mic_kill is False
    assert main(["mic", "status"]) == 0
    assert "released" in capsys.readouterr().out


def test_firewall_grant_uid_persists(isolated_state, capsys, cli):
    assert main(["firewall", "allow", "uid", "101"]) == 0
    st = load_state(isolated_state)
    assert st.granted_uids == [101]
    assert "granted" in capsys.readouterr().out

    # show reflects the grant
    assert main(["firewall", "show"]) == 0
    assert "meta skuid 101 accept" in capsys.readouterr().out

    assert main(["firewall", "deny", "uid", "101"]) == 0
    assert load_state(isolated_state).granted_uids == []


def test_firewall_grant_domain_validated(isolated_state, capsys, cli):
    assert main(["firewall", "allow", "domain", "CDN.Example.COM."]) == 0
    assert load_state(isolated_state).granted_domains == ["cdn.example.com"]

    assert main(["firewall", "allow", "domain", "not a domain"]) == 1
    assert "not a valid domain" in capsys.readouterr().err


def test_firewall_grant_uid_must_be_numeric(isolated_state, capsys, cli):
    assert main(["firewall", "allow", "uid", "root"]) == 1
    assert "must be numeric" in capsys.readouterr().err


def test_status_includes_runtime_probes(capsys, cli):
    assert main(["status"]) == 0
    out = json.loads(capsys.readouterr().out)
    # config-derived
    assert out["firewall_default_deny"] is True
    assert out["mic_kill"] is False
    # runtime probes (values depend on host; keys are contractual)
    for key in ("firewall", "mic_rules", "dns", "waydroid"):
        assert key in out
    assert out["granted_uids"] == []
    assert out["granted_domains"] == []


def test_audit_tail_empty(capsys, cli, monkeypatch, tmp_path):
    from campd import audit as auditmod

    monkeypatch.setattr(auditmod, "DEFAULT_LOG_PATH", tmp_path / "d.log")
    assert main(["audit", "tail"]) == 0
    assert "audit log empty" in capsys.readouterr().out


def test_audit_ingest_and_tail_roundtrip(capsys, cli, monkeypatch, tmp_path):
    from campd import audit as auditmod

    line = ('campd-denied: SRC=192.168.1.50 DST=203.0.113.7 PROTO=TCP '
            'DPT=443 VERDICT=drop')

    class FakeJournal:
        def __call__(self, cmd, **kwargs):
            assert cmd[0] == "journalctl"

            class R:
                stdout = (line + "\n").encode()

            return R()

    monkeypatch.setattr(auditmod, "DEFAULT_LOG_PATH", tmp_path / "d.log")
    monkeypatch.setattr(auditmod.subprocess, "run", FakeJournal())

    assert main(["audit", "ingest"]) == 0
    assert "1 new entries ingested" in capsys.readouterr().out
    assert main(["audit", "tail"]) == 0
    assert "203.0.113.7:443" in capsys.readouterr().out
