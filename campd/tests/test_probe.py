from pathlib import Path

from campd.probe import probe_dns, probe_firewall, probe_mic_rules, probe_waydroid


class FakeRunner:
    def __init__(self, returncode=0, stdout="", missing=False):
        self.returncode = returncode
        self.stdout = stdout
        self.missing = missing

    def __call__(self, cmd, **kwargs):
        if self.missing:
            raise FileNotFoundError(cmd[0])

        class Result:
            pass

        r = Result()
        r.returncode = self.returncode
        r.stdout = self.stdout
        return r


def test_firewall_active():
    assert probe_firewall(runner=FakeRunner(returncode=0)) == "active"


def test_firewall_inactive():
    assert probe_firewall(runner=FakeRunner(returncode=1)) == "inactive"


def test_firewall_unavailable_on_dev_machine():
    assert probe_firewall(runner=FakeRunner(missing=True)) == "unavailable"


def test_dns_probe(tmp_path: Path):
    conf = tmp_path / "campd.conf"
    assert probe_dns(conf) == "absent"
    conf.write_text("x")
    assert probe_dns(conf) == "configured"


def test_mic_rules_probe(tmp_path: Path):
    rules = tmp_path / "99-campd-mic.rules"
    assert probe_mic_rules(rules) == "absent"
    rules.write_text("x")
    assert probe_mic_rules(rules) == "installed"


def test_waydroid_probes():
    assert probe_waydroid(runner=FakeRunner(stdout="RUNNING\n")) == "running"
    assert probe_waydroid(runner=FakeRunner(stdout="FROZEN\n")) == "frozen"
    assert probe_waydroid(runner=FakeRunner(stdout="STOPPED\n")) == "stopped"
    assert probe_waydroid(runner=FakeRunner(stdout="")) == "unknown"
    assert probe_waydroid(runner=FakeRunner(missing=True)) == "unavailable"
