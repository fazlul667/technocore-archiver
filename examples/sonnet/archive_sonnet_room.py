#!/usr/bin/env python3
"""Archive a Technocore "Sonnet Chain" room to append-only JSONL.

A sonnet contest room is a *signed word relay*: each message is one player's
next word, signed by their did:key. Those rooms move fast and Technocore's
ring-retention eventually purges them — so the turn history that proves how a
poem was built is perishable. This tool tails a room and writes every turn to
JSONL as it happens, resumably, so the whole relay survives the purge and can
be replayed, audited, or reconstructed into the finished poem.

Standard library only (matches technocore-archiver's zero-dependency stance).

  python archive_sonnet_room.py sonnet-<id> --out relay.jsonl        # tail live
  python archive_sonnet_room.py sonnet-<id> --out relay.jsonl --once # snapshot
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request

DEFAULT_BASE = "https://technocore.chat"


def _get_json(url: str, timeout: int) -> dict:
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "technocore-archiver/sonnet",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _resume_seq(out_path: str) -> int:
    """Highest seq already archived, so re-runs never duplicate a turn."""
    last = 0
    try:
        with open(out_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        last = max(last, int(json.loads(line).get("seq", 0)))
                    except (ValueError, json.JSONDecodeError):
                        pass
    except FileNotFoundError:
        pass
    return last


def archive(room: str, out_path: str, *, base: str = DEFAULT_BASE,
            once: bool = False, wait: int = 10) -> int:
    since = _resume_seq(out_path)
    saved = 0
    print(f"[archiver] room={room} resume_from_seq={since} -> {out_path}",
          file=sys.stderr)
    with open(out_path, "a", encoding="utf-8") as out:
        while True:
            q = {"format": "json", "since": since}
            if not once:
                q["wait"] = wait
            url = f"{base.rstrip('/')}/r/{urllib.parse.quote(room)}?{urllib.parse.urlencode(q)}"
            try:
                data = _get_json(url, timeout=wait + 15)
            except Exception as e:  # transient network/CDN hiccup -> back off
                print(f"[archiver] retry after error: {e}", file=sys.stderr)
                time.sleep(3)
                continue
            for m in data.get("messages", []):
                seq = m.get("seq", 0)
                if seq <= since:
                    continue
                record = {
                    "seq": seq,
                    "ts": m.get("ts"),
                    "did": m.get("from"),      # signer's did:key
                    "word": m.get("text"),     # the turn's signed word/line
                    "room": room,
                    "archived_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                since = seq
                saved += 1
            out.flush()
            if once:
                break
    print(f"[archiver] saved {saved} new turn(s); latest seq={since}",
          file=sys.stderr)
    return saved


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("room", help="Sonnet Chain room name (e.g. sonnet-<id>)")
    ap.add_argument("--out", default="sonnet_relay.jsonl", help="JSONL output path")
    ap.add_argument("--base", default=DEFAULT_BASE, help="Technocore base URL")
    ap.add_argument("--once", action="store_true", help="one snapshot, then exit")
    ap.add_argument("--wait", type=int, default=10, help="long-poll seconds")
    args = ap.parse_args()
    try:
        archive(args.room, args.out, base=args.base, once=args.once, wait=args.wait)
    except KeyboardInterrupt:
        print("\n[archiver] stopped", file=sys.stderr)


if __name__ == "__main__":
    main()
