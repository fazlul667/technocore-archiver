"""Tests for the incremental archiver using a stubbed HTTP layer."""
import json

from technocore_archiver import Archiver


class FakeArchiver(Archiver):
    """Archiver whose page reads come from an in-memory list."""

    def __init__(self, pages):
        super().__init__()
        self._pages = pages  # list of (since -> rows) responses in call order
        self._i = 0

    def _read_page(self, room, since):  # type: ignore[override]
        page = self._pages[self._i] if self._i < len(self._pages) else []
        self._i += 1
        return page


def test_export_writes_jsonl_and_advances_cursor(tmp_path):
    pages = [
        [{"seq": 1, "ts": "t1", "from": "a", "text": "one"},
         {"seq": 2, "ts": "t2", "from": "b", "text": "two"}],
        [],  # caught up
    ]
    arch = FakeArchiver(pages)
    out = tmp_path / "lobby.jsonl"
    n = arch.export_room("lobby", out)
    assert n == 2
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert [json.loads(x)["text"] for x in lines] == ["one", "two"]
    assert arch.cursors["lobby"] == 2


def test_cursor_skips_already_seen(tmp_path):
    arch = FakeArchiver([[{"seq": 1, "ts": "t", "from": "a", "text": "old"}], []])
    arch.cursors["lobby"] = 1  # already archived seq 1
    out = tmp_path / "lobby.jsonl"
    assert arch.export_room("lobby", out) == 0
    assert not out.exists() or out.read_text() == ""


def test_cursor_roundtrip(tmp_path):
    arch = Archiver()
    arch.cursors = {"lobby": 42}
    path = tmp_path / "cur.json"
    arch.save_cursors(path)
    other = Archiver()
    other.load_cursors(path)
    assert other.cursors == {"lobby": 42}
