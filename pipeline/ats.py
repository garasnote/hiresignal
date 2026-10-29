#!/usr/bin/env python3
"""Build the ATS warehouse: Parquet snapshot -> DuckDB star schema -> marts.

    python3 pipeline/ats.py                          # the committed sample
    python3 pipeline/ats.py --parquet /path/full.parquet

The heavy lifting is SQL; this file only opens the database, runs the two
scripts in order and prints what came out.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
SQL = ROOT / "sql"
DEFAULT_DB = ROOT / "warehouse_ats.duckdb"


def run(parquet: pathlib.Path, db: pathlib.Path) -> None:
    try:
        import duckdb
    except ImportError:
        sys.exit('duckdb is required: pip install -e ".[ats]"')

    con = duckdb.connect(str(db))
    con.execute("pragma threads=4")

    t0 = time.time()
    con.execute((SQL / "ats_schema.sql").read_text().replace("__PARQUET__", parquet.as_posix()))
    schema_s = time.time() - t0

    t1 = time.time()
    con.execute((SQL / "marts_ats.sql").read_text())
    marts_s = time.time() - t1

    q = con.execute("select * from mart_quality").fetchone()
    cols = [d[0] for d in con.description]
    print("warehouse:", db)
    for k, v in zip(cols, q):
        print(f"  {k:<18} {v:,}" if isinstance(v, int) else f"  {k:<18} {v}")
    print(f"  schema {schema_s:.1f}s · marts {marts_s:.1f}s")

    print("\nATS share")
    for ats, n, pct in con.execute("select * from mart_ats_share limit 6").fetchall():
        print(f"  {ats:<12} {n:>7,}  {pct:>5.1f}%")

    print("\ntop countries")
    for country, n, pct in con.execute("select * from mart_top_countries limit 8").fetchall():
        print(f"  {country:<16} {n:>7,}  {pct:>5.1f}%")

    print("\nrole mix")
    for role, n, pct in con.execute("select * from mart_role_mix limit 6").fetchall():
        print(f"  {role:<18} {n:>7,}  {pct:>5.1f}%")
    con.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", default=str(ROOT / "data/sample/postings.parquet"))
    ap.add_argument("--db", default=str(DEFAULT_DB))
    args = ap.parse_args()
    parquet = pathlib.Path(args.parquet)
    if not parquet.exists():
        sys.exit(f"no parquet at {parquet}")
    run(parquet, pathlib.Path(args.db))


if __name__ == "__main__":
    main()
