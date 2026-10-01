from pathlib import Path

from campd.audit import ingest_journal, parse_denied_line

LINE = (
    'campd-denied: IN= OUT=eth0 SRC=192.168.1.50 DST=203.0.113.7 '
    'PROTO=TCP SPT=44300 DPT=443 LEN=60 VERDICT=drop'
)
LINE2 = LINE.replace("203.0.113.7", "198.51.100.9").replace("DPT=443",
                                                            "DPT=8443")


class FakeJournal:
    def __init__(self, text):
        self.text = text

    def __call__(self, cmd, **kwargs):
        assert cmd[0] == "journalctl"
        assert "-k" in cmd

        class Result:
            stdout = self.text.encode()

        return Result()


def test_ingest_appends_new_entries(tmp_path: Path):
    log = tmp_path / "denied.log"
    n = ingest_journal(log_path=log,
                       runner=FakeJournal(f"noise\n{LINE}\n{LINE2}\n"))
    assert n == 2
    assert log.read_text().count("campd-denied") == 2


def test_ingest_dedupes(tmp_path: Path):
    log = tmp_path / "denied.log"
    runner = FakeJournal(f"{LINE}\n")
    ingest_journal(log_path=log, runner=runner)
    n = ingest_journal(log_path=log, runner=runner)
    assert n == 0
    assert log.read_text().count("campd-denied") == 1


def test_ingest_journal_unavailable(tmp_path: Path):
    def missing(cmd, **kwargs):
        raise FileNotFoundError("journalctl")

    assert ingest_journal(log_path=tmp_path / "d.log", runner=missing) == -1


def test_format_entry():
    from campd.audit import format_entry

    e = parse_denied_line(LINE)
    out = format_entry(e)
    assert out == "192.168.1.50 -> 203.0.113.7:443 TCP drop"
