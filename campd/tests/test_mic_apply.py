import subprocess

import pytest

from campd.config import MicConfig
from campd.mic import apply


class RecordingRunner:
    def __init__(self, missing=False):
        self.calls = []
        self.missing = missing

    def __call__(self, cmd, **kwargs):
        if self.missing:
            raise FileNotFoundError(cmd[0])
        self.calls.append(cmd)
        if kwargs.get("check") and cmd[0] == "nope":
            raise subprocess.CalledProcessError(1, cmd)

        class Result:
            returncode = 0

        return Result()


def test_apply_engaged_writes_rules_and_reloads(tmp_path):
    rules = tmp_path / "99-campd-mic.rules"
    pw = tmp_path / "99-campd-mic-kill.conf"
    runner = RecordingRunner()
    ok = apply(MicConfig(kill_switch=True), runner=runner,
               rules_path=rules, pipewire_path=pw)
    assert ok is True
    assert rules.exists() and "pcmC*D*c" in rules.read_text()
    assert pw.exists()
    assert ["udevadm", "control", "--reload-rules"] in runner.calls
    assert any(c[0] == "udevadm" and "--trigger" in " ".join(c)
               or "--action=add" in c for c in runner.calls)


def test_apply_released_removes_artifacts(tmp_path):
    rules = tmp_path / "99-campd-mic.rules"
    pw = tmp_path / "99-campd-mic-kill.conf"
    rules.write_text("old")
    pw.write_text("old")
    ok = apply(MicConfig(kill_switch=False), runner=RecordingRunner(),
               rules_path=rules, pipewire_path=pw)
    assert ok is True
    assert not rules.exists()
    assert not pw.exists()


def test_apply_dev_machine_still_writes_rules(tmp_path):
    rules = tmp_path / "99-campd-mic.rules"
    ok = apply(MicConfig(kill_switch=True), runner=RecordingRunner(missing=True),
               rules_path=rules, pipewire_path=tmp_path / "pw.conf")
    assert ok is False  # udevadm missing
    assert rules.exists()  # but persistence happened
