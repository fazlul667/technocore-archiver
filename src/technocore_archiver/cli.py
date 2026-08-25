"""Command-line entry point: ``technocore-archive``."""
from __future__ import annotations

import argparse
from pathlib import Path

from .archiver import Archiver, DEFAULT_BASE


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="technocore-archive",
        description="Incrementally archive technocore.chat rooms to JSONL.",
    )
    parser.add_argument("rooms", nargs="+", help="room name(s) to archive")
    parser.add_argument("-o", "--out-dir", default="technocore-archive", help="output directory")
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--cursors", default=None, help="cursor file (default: <out-dir>/.cursors.json)")
    parser.add_argument("--loop", type=int, default=0, metavar="SECONDS",
                        help="repeat every N seconds instead of running once")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    cursor_file = Path(args.cursors) if args.cursors else out_dir / ".cursors.json"
    arch = Archiver(base_url=args.base_url)
    arch.load_cursors(cursor_file)

    def run_once() -> None:
        counts = arch.export_rooms(args.rooms, out_dir)
        arch.save_cursors(cursor_file)
        total = sum(counts.values())
        print(f"archived {total} new message(s): " + ", ".join(f"{r}={n}" for r, n in counts.items()))

    if args.loop:
        import time
        while True:
            run_once()
            time.sleep(args.loop)
    else:
        run_once()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
