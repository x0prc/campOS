import pytest

from campd.bootctl import (
    BootctlError,
    active_slot,
    main,
    set_next_slot,
    slots_info,
)

AB_CONF = """\
DEFAULT camp-a
TIMEOUT 5

LABEL camp-a
  MENU LABEL campOS A
  LINUX /vmlinuz-a
  APPEND root=/dev/mmcblk0p3 camp.slot=a
  INITRD /initrd-a.img

LABEL camp-b
  MENU LABEL campOS B
  LINUX /vmlinuz-b
  APPEND root=/dev/mmcblk0p4 camp.slot=b
  INITRD /initrd-b.img
"""

SINGLE_CONF = """\
DEFAULT Armbian
LABEL Armbian
  LINUX /vmlinuz
  APPEND root=UUID=xyz
"""


@pytest.fixture
def conf(tmp_path):
    path = tmp_path / "extlinux.conf"
    path.write_text(AB_CONF)
    return path


class NoFindmnt:
    """Runner where findmnt/blkid don't exist (dev machine)."""

    def __call__(self, cmd, **kwargs):
        raise FileNotFoundError(cmd[0])


def test_active_from_cmdline(tmp_path, monkeypatch):
    cmd = tmp_path / "cmdline"
    cmd.write_text("console=ttyAML0 camp.slot=b root=/dev/mmcblk0p4")
    monkeypatch.setenv("CAMPD_CMDLINE", str(cmd))
    assert active_slot(conf_path=tmp_path / "missing") == "b"


def test_active_fallback_to_default_entry(tmp_path, monkeypatch, conf):
    monkeypatch.setenv("CAMPD_CMDLINE", str(tmp_path / "nocmdline"))
    assert active_slot(conf_path=conf, runner=NoFindmnt()) == "a"


def test_active_raises_when_undeterminable(tmp_path, monkeypatch, conf):
    monkeypatch.setenv("CAMPD_CMDLINE", str(tmp_path / "nocmdline"))
    single = tmp_path / "single.conf"
    single.write_text(SINGLE_CONF)
    with pytest.raises(BootctlError):
        active_slot(conf_path=single, runner=NoFindmnt())


def test_slots_info_ab(conf):
    info = slots_info(conf_path=conf)
    assert info["ab"] is True
    assert info["entries"] == ["camp-a", "camp-b"]
    assert info["default"] == "camp-a"


def test_slots_info_single_slot(tmp_path):
    path = tmp_path / "extlinux.conf"
    path.write_text(SINGLE_CONF)
    info = slots_info(conf_path=path)
    assert info["ab"] is False
    assert info["default"] == "Armbian"


def test_set_next_slot_flips_and_backups(conf):
    entry = set_next_slot("b", conf_path=conf)
    assert entry == "camp-b"
    assert "DEFAULT camp-b" in conf.read_text()
    bak = conf.with_suffix(".conf.bak")
    assert bak.exists()
    assert "DEFAULT camp-a" in bak.read_text()  # backup of original

    # flip back
    set_next_slot("a", conf_path=conf)
    assert "DEFAULT camp-a" in conf.read_text()


def test_set_next_slot_other_uses_active(tmp_path, monkeypatch, conf):
    cmd = tmp_path / "cmdline"
    cmd.write_text("camp.slot=a")
    monkeypatch.setenv("CAMPD_CMDLINE", str(cmd))
    entry = set_next_slot("other", conf_path=conf, runner=NoFindmnt())
    assert entry == "camp-b"


def test_set_next_slot_refuses_single_slot(tmp_path):
    path = tmp_path / "extlinux.conf"
    path.write_text(SINGLE_CONF)
    original = path.read_text()
    with pytest.raises(BootctlError, match="single-slot"):
        set_next_slot("b", conf_path=path)
    assert path.read_text() == original  # untouched


def test_set_next_slot_missing_conf(tmp_path):
    with pytest.raises(BootctlError, match="not found"):
        set_next_slot("a", conf_path=tmp_path / "nope.conf")


def test_cli_active_slot_undeterminable(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CAMPD_CMDLINE", str(tmp_path / "none"))
    monkeypatch.setenv("CAMPD_EXTLINUX", "/nonexistent")
    assert main(["active-slot"]) == 1
    assert "error:" in capsys.readouterr().err


def test_cli_set_next_slot_on_ab_conf(conf, capsys, monkeypatch):
    monkeypatch.setenv("CAMPD_EXTLINUX", str(conf))
    assert main(["set-next-slot", "b"]) == 0
    assert "next boot: camp-b" in capsys.readouterr().out
    assert "DEFAULT camp-b" in conf.read_text()


def test_cli_error_exit(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("CAMPD_EXTLINUX", str(tmp_path / "absent.conf"))
    assert main(["set-next-slot", "b"]) == 1
    assert "error:" in capsys.readouterr().err
