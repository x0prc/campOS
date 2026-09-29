import pytest

from campd.config import WaydroidConfig
from campd.reset import ResetError, factory_reset
from campd.supervisor import Supervisor


class FakeRunner:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def __call__(self, cmd, **kwargs):
        self.calls.append(cmd)
        if self.fail:
            raise RuntimeError("command failed")

        class Result:
            stdout = b"slot-b\n"

        return Result()


def test_supervisor_start_loads_binder_on_demand():
    runner = FakeRunner()
    sup = Supervisor(WaydroidConfig(), runner=runner)
    sup.start()
    assert ["modprobe", "binder_linux"] in runner.calls
    assert ["waydroid", "session", "start"] in runner.calls


def test_supervisor_stop_unloads_binder():
    runner = FakeRunner()
    sup = Supervisor(WaydroidConfig(), runner=runner)
    sup.start()
    runner.calls.clear()
    sup.stop()
    assert ["waydroid", "session", "stop"] in runner.calls
    assert ["rmmod", "binder_linux"] in runner.calls


def test_factory_reset_requires_confirmation():
    with pytest.raises(ResetError):
        factory_reset(confirm=False)


def test_factory_reset_flips_slot_and_wipes_data():
    runner = FakeRunner()
    factory_reset(confirm=True, data_path="/data", runner=runner)
    assert ["camp-bootctl", "set-next-slot", "other"] in runner.calls
    assert ["rm", "-rf", "/data/*"] in runner.calls
