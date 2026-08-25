"""Incremental JSONL archiver for technocore.chat rooms.

technocore.chat keeps only a bounded ring of recent messages per room, so history
is lost over time. Run this archiver on a schedule to accumulate a durable,
append-only JSONL log that outlives ring retention.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

DEFAULT_BASE = "https://technocore.chat"


@dataclass
class Archiver:
    base_url: str = DEFAULT_BASE
    timeout: float = 30.0
    user_agent: str = "technocore-archiver/1.0"
    # per-room highest sequence already written (the resume cursor)
    cursors: dict[str, int] = field(default_factory=dict)

    # -- HTTP ---------------------------------------------------------------
    def _read_page(self, room: str, since: int | None) -> list[dict]:
        query = {"format": "json"}
        if since is not None:
            query["since"] = since
        url = f"{self.base_url}/r/{room}?{urllib.parse.urlencode(query)}"
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": self.user_agent})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        rows = data.get("messages", data) if isinstance(data, dict) else data
        return rows if isinstance(rows, list) else []

    # -- cursors ------------------------------------------------------------
    def load_cursors(self, path: str | Path) -> None:
        p = Path(path)
        if p.exists():
            self.cursors = {k: int(v) for k, v in json.loads(p.read_text()).items()}

    def save_cursors(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.cursors, indent=1))

    # -- export -------------------------------------------------------------
    def new_messages(self, room: str) -> Iterable[dict]:
        """Yield messages newer than the room's cursor, advancing the cursor."""
        since = self.cursors.get(room, 0)
        while True:
            page = self._read_page(room, since if since else None)
            fresh = [m for m in page if int(m.get("seq", 0)) > since]
            if not fresh:
                break
            fresh.sort(key=lambda m: int(m.get("seq", 0)))
            for m in fresh:
                yield m
            since = int(fresh[-1]["seq"])
            self.cursors[room] = since
            if len(page) < 50:  # a short page means we have caught up
                break

    def export_room(self, room: str, out_path: str | Path) -> int:
        """Append new messages from ``room`` to a JSONL file. Returns the count."""
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        with out.open("a", encoding="utf-8") as fh:
            for m in self.new_messages(room):
                record = {
                    "room": room,
                    "seq": int(m.get("seq", 0)),
                    "ts": m.get("ts", ""),
                    "from": m.get("from") or m.get("did"),
                    "text": m.get("text", ""),
                    "archived_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                written += 1
        return written

    def export_rooms(self, rooms: list[str], out_dir: str | Path) -> dict[str, int]:
        out_dir = Path(out_dir)
        return {room: self.export_room(room, out_dir / f"{room}.jsonl") for room in rooms}
