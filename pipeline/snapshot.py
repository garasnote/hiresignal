#!/usr/bin/env python3
"""Append today's snapshot to docs/data/timeline.json.

    python3 pipeline/snapshot.py --parquet /path/postings_all.parquet

The site's static dashboard always shows the latest snapshot; the timeline shows
what changed between them. Running twice on the same day is a no-op, so a cron
that fires twice never double-counts a day.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dashboard.metrics import from_duckdb  # noqa: E402

TIMELINE = ROOT / "docs/data/timeline.json"


def build_warehouse(parquet: pathlib.Path) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        db = pathlib.Path(tmp) / "snapshot.duckdb"
        subprocess.run([sys.executable, str(ROOT / "pipeline/ats.py"),
                        "--parquet", str(parquet), "--db", str(db)],
                       check=True, stdout=subprocess.DEVNULL)
        return from_duckdb(db)


def entry(m: dict, day: str, boards: int | None = None) -> dict:
    out = {
        "date": day,
        "scope": "panel" if boards else "full",
        "landed": m["landed"],
        "kept": m["kept"],
        "companies": m["companies"],
        "remote_pct": m["remote_pct"],
        "junior": m["junior"],
        "body_date": m["body_date"],
        "ats": {name: n for name, n in m["ats"]},
    }
    if boards:
        out["boards"] = boards
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", required=True)
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--timeline", default=str(TIMELINE))
    ap.add_argument("--boards", type=int, default=0,
                    help="how many boards this snapshot covers (a fixed panel, not the whole market)")
    a = ap.parse_args()

    path = pathlib.Path(a.timeline)
    data = json.loads(path.read_text()) if path.exists() else {"snapshots": []}
    scope = "panel" if a.boards else "full"
    for s in data["snapshots"]:
        s.setdefault("scope", "full")
    taken = {(s["date"], s.get("scope", "full")) for s in data["snapshots"]}

    if (a.date, scope) in taken:
        print(f"{a.date} ({scope}) already recorded — nothing to do")
        return

    m = build_warehouse(pathlib.Path(a.parquet))
    data["snapshots"].append(entry(m, a.date, a.boards or None))
    data["snapshots"].sort(key=lambda s: s["date"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1) + "\n")
    print(f"{a.date}: {m['kept']:,} postings · {m['companies']:,} companies "
          f"· timeline has {len(data['snapshots'])} day(s)")


if __name__ == "__main__":
    main()
