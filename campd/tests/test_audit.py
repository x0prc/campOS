from pathlib import Path

from campd.audit import DeniedEntry, parse_denied_line, tail_denied

LINE = (
    'campd-denied: IN= OUT=eth0 SRC=192.168.1.50 DST=203.0.113.7 '
    'PROTO=TCP SPT=44300 DPT=443 LEN=60 VERDICT=drop'
)


def test_parse_campd_line():
    entry = parse_denied_line(LINE)
    assert isinstance(entry, DeniedEntry)
    assert entry.src_ip == "192.168.1.50"
    assert entry.dst_ip == "203.0.113.7"
    assert entry.dport == 443
    assert entry.proto == "TCP"
    assert entry.verdict == "drop"


def test_ignore_non_campd_lines():
    assert parse_denied_line("random kernel message") is None


def test_tail_reads_only_campd_entries(tmp_path: Path):
    log = tmp_path / "denied.log"
    log.write_text(LINE + "\nnoise\n" + LINE + "\n")
    entries = tail_denied(log)
    assert len(entries) == 2


def test_tail_missing_file(tmp_path: Path):
    assert tail_denied(tmp_path / "absent.log") == []
