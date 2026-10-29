#!/usr/bin/env python3
"""Wrap the dashboard SVG in a one-page site, ready for GitHub Pages.

    python3 dashboard/build_site.py --json docs/data/marts.json --out _site/index.html

Stdlib only: the page is HTML plus an inline SVG, so Pages can serve it without
a build step and without a chart library.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from dashboard.build_svg import svg  # noqa: E402
from dashboard.metrics import from_json  # noqa: E402

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HireSignal — the 2026 ATS harvest</title>
<meta name="description" content="231,859 job postings from eleven applicant-tracking systems, deduplicated and modelled into a star schema.">
<meta name="color-scheme" content="dark">
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  html, body {{ background: #070a0e; }}
  body {{ margin: 0; color: #e9eff5;
         font-family: Inter, -apple-system, Segoe UI, Helvetica, Arial, sans-serif;
         -webkit-font-smoothing: antialiased; }}
  .bar {{ display: flex; align-items: center; justify-content: space-between; gap: 24px;
          max-width: 1240px; margin: 0 auto; padding: 20px 24px 18px;
          border-bottom: 1px solid #131c26; }}
  .brand {{ color: #e9eff5; text-decoration: none; font-weight: 650; letter-spacing: .01em;
            font-size: 14px; display: inline-flex; align-items: center; gap: 9px; }}
  .dot {{ width: 7px; height: 7px; border-radius: 50%; background: #4cc2e0;
          box-shadow: 0 0 12px #4cc2e0; }}
  nav {{ display: flex; gap: 20px; font-size: 13px; flex-wrap: wrap; }}
  nav a {{ color: #7e8fa2; text-decoration: none; transition: color .15s ease; }}
  nav a:hover {{ color: #4cc2e0; }}
  main {{ max-width: 1240px; margin: 0 auto; padding: 22px 24px 56px; }}
  .frame {{ border-radius: 16px; overflow: hidden; border: 1px solid #131c26;
            box-shadow: 0 24px 60px -30px rgba(0,0,0,.9); }}
  .frame svg {{ display: block; width: 100%; height: auto; }}
  footer {{ display: flex; justify-content: space-between; gap: 28px; flex-wrap: wrap;
            padding: 20px 2px 0; color: #55677a; font-size: 12.5px; line-height: 1.65; }}
  footer p {{ margin: 0; max-width: 70ch; }}
  code {{ color: #8ea3b8; font-size: 12px; }}
  @media (max-width: 720px) {{
    .bar {{ flex-direction: column; align-items: flex-start; gap: 10px; }}
    nav {{ gap: 14px; }}
  }}
</style>
</head>
<body>
<div class="bar">
  <a class="brand" href="https://garasnote.github.io/hiresignal/"><span class="dot"></span>HireSignal</a>
  <nav>
    <a href="https://github.com/garasnote/hiresignal">source</a>
    <a href="https://github.com/garasnote/hiresignal/blob/main/sql/ats_schema.sql">schema</a>
    <a href="https://github.com/garasnote/hiresignal/blob/main/sql/marts_ats.sql">marts</a>
    <a href="https://github.com/garasnote/rag-service">retrieval over the same corpus</a>
  </nav>
</div>
<main>
  <div class="frame">
{dashboard}
  </div>
  <footer>
    <p>Built by <code>pipeline/ats.py</code> (DuckDB) and <code>dashboard/build_site.py</code>.
    Numbers come from <code>docs/data/marts.json</code>, regenerated from the full snapshot; the repo
    ships a 5,588-row sample so the pipeline runs without the 111&nbsp;MB file. Countries are parsed
    from the location string, and {unknown_pct:.1f}% stays <code>unknown</code> rather than guessed.</p>
    <p>Timeline: {timeline_note}.</p>
  </footer>
</main>
</body>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="docs/data/marts.json")
    ap.add_argument("--timeline", default="docs/data/timeline.json")
    ap.add_argument("--out", default="_site/index.html")
    a = ap.parse_args()

    m = from_json(a.json)
    tl = pathlib.Path(a.timeline)
    timeline = json.loads(tl.read_text()) if tl.exists() else None
    snaps = [x for x in ((timeline or {}).get("snapshots") or [])
             if x.get("scope") == "panel" or x.get("boards")]
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(PAGE.format(
        dashboard=svg(m, timeline),
        unknown_pct=m.get("unknown_pct", 0.0),
        timeline_note=(f"{len(snaps)} daily snapshot{'s' if len(snaps) != 1 else ''}, "
                       f"first {snaps[0]['date']}" if snaps else "no snapshots yet")))
    print(f"{out} · {m['kept']:,} postings · {len(m['ats'])} platforms")


if __name__ == "__main__":
    main()
