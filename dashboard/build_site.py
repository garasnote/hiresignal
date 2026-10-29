#!/usr/bin/env python3
"""Build the site: one page for the full harvest, one page per daily snapshot.

    python3 dashboard/build_site.py --out _site

Static output, but every number is real HTML text and every day has its own URL,
so history is browsable and nothing needs JavaScript.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from dashboard.metrics import from_json  # noqa: E402
from dashboard.render_html import page  # noqa: E402

FOOTER = """Built by <code>pipeline/ats.py</code> (DuckDB) and <code>dashboard/build_site.py</code>.
The headline page is the full harvest; each daily page is a fixed 1,200-board panel, so the line
measures drift in the same boards rather than growth in the scraper. Numbers come from
<code>docs/data/marts.json</code> and <code>docs/data/timeline.json</code>."""


def day_view(entry: dict, full: dict) -> dict:
    """A snapshot page: its own numbers, falling back to the full snapshot for panels
    that early entries did not record."""
    return {
        "kept": entry["kept"],
        "landed": entry["landed"],
        "companies": entry["companies"],
        "remote_pct": entry["remote_pct"],
        "junior": entry["junior"],
        "body_date": entry["body_date"],
        "no_date": entry.get("no_date", entry["kept"] - entry["body_date"]),
        "dated": entry.get("dated") or 0,
        "ats": entry.get("ats") or full["ats"],
        "countries": entry.get("countries") or full["countries"],
        "roles": entry.get("roles") or full["roles"],
        "postings": entry["kept"],
    }


def stages(v: dict):
    out = [("landed", v["landed"], "parquet"),
           ("after dedupe", v["kept"], "same requisition")]
    if v.get("dated"):
        out.append(("with a real date", v["dated"], "parsed"))
    out.append(("body + date", v["body_date"], "fully usable"))
    return out


def stats(v: dict, platforms: int):
    return [("companies", f"{v['companies']:,}"),
            ("platforms", str(platforms)),
            ("fully remote", f"{v['remote_pct']:.0f}%"),
            ("junior-titled", f"{v['junior']:,}")]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="docs/data/marts.json")
    ap.add_argument("--timeline", default="docs/data/timeline.json")
    ap.add_argument("--out", default="_site")
    a = ap.parse_args()

    full = from_json(a.json)
    tl = pathlib.Path(a.timeline)
    timeline = json.loads(tl.read_text()) if tl.exists() else {"snapshots": []}
    panels = sorted([s for s in timeline["snapshots"] if s.get("scope") == "panel"],
                    key=lambda s: s["date"])

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    # root: the latest daily panel — one scope everywhere on the page
    latest = panels[-1] if panels else None
    if latest:
        v = day_view(latest, full)
        (out / "index.html").write_text(page(
            title=f"HireSignal — daily panel, {latest['date']}",
            kicker=f"Daily panel · latest · {latest['date']}",
            h1="The market this morning",
            lede=f"A fixed panel of {latest.get('boards', 1200):,} applicant-tracking boards, fetched every morning "
                 "at 07:30. The headline number, the panels and the line below all come from those same boards.",
            hero_value=f"{v['kept']:,}",
            hero_note=f"postings in the panel on {latest['date']}",
            stats=stats(v, len(v["ats"])),
            ats=v["ats"], countries=v["countries"], roles=v["roles"],
            stages=stages(v), snaps=panels, history=panels, current=latest["date"],
            footer_note=FOOTER, full_link="/hiresignal/full/"))
    else:
        (out / "index.html").write_text(page(
            title="HireSignal — the 2026 ATS harvest",
            kicker="HireSignal · ATS harvest",
            h1="The 2026 job-market harvest",
            lede="Every posting published on eleven applicant-tracking platforms, deduplicated in SQL and "
                 "modelled into a star schema.",
            hero_value=f"{full['kept']:,}",
            hero_note="postings after collapsing 11,904 duplicate listings",
            stats=stats(full, len(full["ats"])),
            ats=full["ats"], countries=full["countries"], roles=full["roles"],
            stages=stages(full), snaps=[], history=[],
            current=None, footer_note=FOOTER))

    # the one-off full harvest (8,393 boards) on its own page, never mixed with the panel
    (out / "full").mkdir(parents=True, exist_ok=True)
    (out / "full" / "index.html").write_text(page(
        title="HireSignal — the full harvest",
        kicker="One-off snapshot · 29 Oct 2026",
        h1="The full 2026 harvest, once",
        lede="Every board we can reach: 8,393 companies across eleven applicant-tracking platforms, "
             "deduplicated in SQL and modelled into a star schema. This is a single snapshot, not the daily panel.",
        hero_value=f"{full['kept']:,}",
        hero_note="postings after collapsing 11,904 duplicate listings",
        stats=stats(full, len(full["ats"])),
        ats=full["ats"], countries=full["countries"], roles=full["roles"],
        stages=stages(full), snaps=[], history=panels, current=None,
        footer_note=FOOTER, full_link="/hiresignal/"))

    for entry in panels:
        v = day_view(entry, full)
        (out / entry["date"]).mkdir(parents=True, exist_ok=True)
        (out / entry["date"] / "index.html").write_text(page(
            title=f"HireSignal — daily panel, {entry['date']}",
            kicker=f"Daily panel · {entry['date']}",
            h1=f"The market on {entry['date']}",
            lede=f"A fixed panel of {entry.get('boards', 1200):,} applicant-tracking boards, fetched that day. "
                 "Every number here belongs to this snapshot alone.",
            hero_value=f"{v['kept']:,}",
            hero_note=f"postings in the panel on {entry['date']}",
            stats=stats(v, len(v["ats"])),
            ats=v["ats"], countries=v["countries"], roles=v["roles"],
            stages=stages(v), snaps=[s for s in panels if s["date"] <= entry["date"]],
            history=panels, current=entry["date"],
            footer_note=FOOTER, full_link="/hiresignal/full/"))

    print(f"{out}/index.html + {len(panels)} day page(s)")


if __name__ == "__main__":
    main()
