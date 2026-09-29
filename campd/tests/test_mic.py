from campd.config import MicConfig
from campd.mic import (
    render_udev_rules,
    render_pipewire_mute_snippet,
    waydroid_has_mic,
)


def test_rules_absent_when_kill_released():
    cfg = MicConfig(kill_switch=False)
    assert render_udev_rules(cfg) == ""
    assert render_pipewire_mute_snippet(cfg) == ""
    assert waydroid_has_mic(cfg) is True


def test_rules_present_when_kill_engaged():
    cfg = MicConfig(kill_switch=True)
    rules = render_udev_rules(cfg)
    assert 'SUBSYSTEM=="sound"' in rules
    assert 'KERNEL=="pcmC*D*c"' in rules


def test_selective_blocking():
    cfg = MicConfig(kill_switch=True, block_usb_mics=False)
    rules = render_udev_rules(cfg)
    assert "bInterfaceClass" not in rules
    assert "pcmC*D*c" in rules


def test_waydroid_mic_denied_while_killed():
    cfg = MicConfig(kill_switch=True)
    assert waydroid_has_mic(cfg) is False
