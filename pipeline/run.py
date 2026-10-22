#!/usr/bin/env python3
"""Run the whole pipeline: scrape -> raw -> star schema -> marts -> CSV exports.

    python3 pipeline/run.py --offline        # fixture, no network (used by CI)
    python3 pipeline/run.py --live           # scrape both boards (~1-2 min)
    python3 pipeline/run.py --live --enrich 15   # also read experience from 15 detail pages
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import sources
import warehouse


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--offline", action="store_true", help="use fixtures/sample_offers.json")
    p.add_argument("--live", action="store_true", help="scrape the boards")
    p.add_argument("--enrich", type=int, default=0, metavar="N",
                   help="read 'Experiencia mínima' from N detail pages")
    p.add_argument("--tracker", default=None, help="path to job_tracker/data.json")
    args = p.parse_args()

    if not (args.offline or args.live):
        p.error("choose --offline or --live")

    print("1/3  fetching postings…")
    offers = sources.scrape_all(offline=args.offline)
    print(f"     {len(offers)} postings")

    if args.enrich:
        print(f"2/3  enriching experience on up to {args.enrich} detail pages…")
        warehouse.enrich_experience(offers, limit=args.enrich)
        got = sum(1 for o in offers if o.get("experience_years") is not None)
        print(f"     experience known for {got}/{len(offers)}")
    else:
        print("2/3  skipping enrichment")

    print("3/3  loading warehouse + building marts…")
    warehouse.load(offers, tracker_path=args.tracker)
    marts = warehouse.export_marts()
    print(f"     {warehouse.DB.name} written, {len(marts)} marts exported to exports/")
    for name, rows in marts:
        print(f"       {name:28s} {rows:5d} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
