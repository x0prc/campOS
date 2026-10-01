import json

import pytest

from campd.config import CampConfig, FirewallConfig, MicConfig
from campd.state import (
    RuntimeState,
    effective_firewall,
    effective_mic,
    load_state,
    save_state,
)


def test_defaults_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("CAMPD_STATE_PATH", str(tmp_path / "state.json"))
    st = load_state()
    assert st == RuntimeState()


def test_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    st = RuntimeState(mic_kill=True, granted_uids=[101],
                      granted_domains=["cdn.example.com"])
    save_state(st, path)
    assert load_state(path) == st


def test_corrupt_state_fails_open(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{not json")
    st = load_state(path)
    assert st.mic_kill is False
    assert st.granted_uids == []


def test_save_is_atomic_replace(tmp_path):
    path = tmp_path / "state.json"
    save_state(RuntimeState(mic_kill=True), path)
    save_state(RuntimeState(mic_kill=False), path)
    data = json.loads(path.read_text())
    assert data["mic_kill"] is False
    assert not list(tmp_path.glob("*.tmp"))


def test_effective_firewall_merges_grants():
    cfg = CampConfig(firewall=FirewallConfig(
        allowed_outbound_uids=[101], allowed_domains=["a.example"]))
    st = RuntimeState(granted_uids=[102, 101],
                      granted_domains=["b.example", "a.example"])
    eff = effective_firewall(cfg, st)
    assert eff.allowed_outbound_uids == [101, 102]  # deduped, order kept
    assert eff.allowed_domains == ["a.example", "b.example"]
    assert eff.default_deny is True


def test_effective_mic_uses_stronger_signal():
    cfg = CampConfig(mic=MicConfig(kill_switch=False))
    assert effective_mic(cfg, RuntimeState(mic_kill=True)).kill_switch is True
    assert effective_mic(cfg, RuntimeState()).kill_switch is False
    # build policy can force kill even if runtime state says off
    forced = CampConfig(mic=MicConfig(kill_switch=True))
    assert effective_mic(forced, RuntimeState(mic_kill=False)).kill_switch
