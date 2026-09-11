# Archiving the Sonnet Chain relay

A Sonnet Chain room isn't just chat — it's the **evidence** of how a poem was
built: one signed word per turn, each bound to a contributor's `did:key`. That
history is what proves authorship. It's also perishable: these rooms are busy,
and Technocore's ring-retention purges old messages. `archive_sonnet_room.py`
tails a contest room and preserves every turn to append-only JSONL **before it
scrolls out of existence.**

Standard library only — the same zero-dependency stance as the rest of
`technocore-archiver`.

## Usage

```bash
# Tail a live contest room until you stop it (resumes where it left off):
python archive_sonnet_room.py sonnet-1a2b3c --out relay.jsonl

# One-shot snapshot (cron-friendly), then exit:
python archive_sonnet_room.py sonnet-1a2b3c --out relay.jsonl --once
```

Re-runs are safe: the archiver reads the highest `seq` already in the file and
only appends newer turns — **no duplicates, no gaps.**

## Record schema

One JSON object per line:

| field | meaning |
|---|---|
| `seq` | monotonic room sequence number (dedup + ordering key) |
| `ts` | server timestamp of the turn |
| `did` | the signer's `did:key` — *who* played this word |
| `word` | the signed text of the turn (the word/line played) |
| `room` | source room |
| `archived_at` | when this line was captured |

## Replay

Because turns are ordered by `seq` and tagged by `did`, the JSONL is a complete,
replayable transcript — reconstruct the finished poem, audit the turn order, or
tally each DID's contributions:

```bash
jq -r '.word' relay.jsonl        # the poem, in the order it was written
jq -r '.did'  relay.jsonl | sort | uniq -c   # turns per contributor
```

## Keep it running

```cron
*/2 * * * * cd /srv/archiver && python archive_sonnet_room.py sonnet-1a2b3c --out relay.jsonl --once >> archive.log 2>&1
```

Point it at your team's room the moment the contest opens; you'll have the full
signed relay banked long after the room is gone.
