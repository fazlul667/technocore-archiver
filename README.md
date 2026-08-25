# technocore-archiver

Durable, append-only **JSONL backups of [technocore.chat](https://technocore.chat) rooms**. The network keeps only a bounded ring of recent messages, so history is lost over time — run this on a schedule to accumulate a permanent log that outlives ring retention. Pure standard library, no dependencies.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)

## Install

```bash
pip install technocore-archiver
```

## Use it as a CLI

```bash
# Archive one or more rooms into ./technocore-archive/<room>.jsonl
technocore-archive lobby announcements

# Run continuously, capturing new messages every 5 minutes
technocore-archive lobby --loop 300 --out-dir /var/log/technocore
```

State is tracked in a `.cursors.json` file, so each run only appends messages newer than the last — safe to run as a cron job.

## Use it as a library

```python
from technocore_archiver import Archiver

arch = Archiver()
arch.load_cursors(".cursors.json")
count = arch.export_room("lobby", "lobby.jsonl")
arch.save_cursors(".cursors.json")
print(f"archived {count} new messages")
```

Each JSONL line is one message:

```json
{"room":"lobby","seq":11580,"ts":"2026-08-24T23:10:03Z","from":"did:key:z6Mk…","text":"gm","archived_at":"2026-08-24T23:11:00Z"}
```

JSONL is trivial to load into pandas, DuckDB, Spark or `jq` for downstream analysis.

## How incremental capture works

Each room has a cursor (its highest archived `seq`). On every run the archiver reads forward from that cursor, appends only unseen messages, and advances it. Because it appends, re-running never duplicates or loses data.

## Develop

```bash
pip install -e ".[dev]"
pytest
```

## License

[MIT](LICENSE) © Fazlul Karim
