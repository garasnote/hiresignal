#!/usr/bin/env python3
"""Wrap the dashboard SVG in a one-page site, ready for GitHub Pages.

    python3 dashboard/build_site.py --json docs/data/marts.json --out _site/index.html

Stdlib only: the page is HTML plus an inline SVG, so Pages can serve it without
a build step and without a chart library.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from dashboard.build_svg import svg  # noqa: E402
from dashboard.metrics import from_json  # noqa: E402
import json  # noqa: E402

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HireSignal — the 2026 ATS harvest</title>
<meta name="description" content="231,859 job postings from eleven applicant-tracking systems, deduplicated and modelled into a star schema.">
<style>
  :root {{ color-scheme: light; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: #f6f7f9; color: #1b2430;
         font-family: Inter, -apple-system, Segoe UI, Helvetica, Arial, sans-serif; }}
  main {{ max-width: 1280px; margin: 0 auto; padding: 40px 24px 56px; }}
  header {{ display: flex; align-items: baseline; justify-content: space-between; gap: 24px;
            flex-wrap: wrap; margin-bottom: 20px; }}
  h1 {{ font-size: 22px; margin: 0 0 6px; letter-spacing: -0.01em; }}
  .sub {{ margin: 0; color: #6b7787; font-size: 13.5px; max-width: 62ch; }}
  .links {{ font-size: 13px; }}
  .links a {{ color: #2f6f8f; text-decoration: none; margin-left: 16px; }}
  .links a:hover {{ text-decoration: underline; }}
  .card {{ background: #fff; border: 1px solid #dfe4ea; border-radius: 10px; padding: 10px;
           overflow-x: auto; }}
  .card svg {{ display: block; width: 100%; height: auto; }}
  footer {{ margin-top: 18px; color: #6b7787; font-size: 12.5px; line-height: 1.6; }}
  footer code {{ background: #eef2f5; padding: 1px 5px; border-radius: 4px; font-size: 12px; }}
</style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>HireSignal — the 2026 ATS harvest</h1>
      <p class="sub">Every posting published on eleven applicant-tracking platforms, deduplicated in SQL
      and modelled into a star schema. The dashboard below is generated from the warehouse marts, not drawn by hand.</p>
    </div>
    <nav class="links">
      <a href="https://github.com/garasnote/hiresignal">source</a>
      <a href="https://github.com/garasnote/hiresignal/blob/main/sql/ats_schema.sql">schema</a>
      <a href="https://github.com/garasnote/rag-service">retrieval over the same corpus</a>
    </nav>
  </header>
  <div class="card">
{dashboard}
  </div>
  <footer>
    Built by <code>pipeline/ats.py</code> (DuckDB) and <code>dashboard/build_site.py</code>.
    Numbers come from <code>docs/data/marts.json</code>, regenerated from the full snapshot;
    the repository ships a 5,588-row sample so the pipeline runs without the 111&nbsp;MB file.
    Timeline: {timeline_note}. Countries are derived from the location string, and {unknown_pct:.1f}% stays <code>unknown</code> rather than guessed.
  </footer>
</main>
</body>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="docs/data/marts.json")
    ap.add_argument("--out", default="_site/index.html")
    a = ap.parse_args()

    m = from_json(a.json)
    tl = pathlib.Path("docs/data/timeline.json")
    timeline = json.loads(tl.read_text()) if tl.exists() else None
    snaps = [x for x in ((timeline or {}).get("snapshots") or [])
             if x.get("scope") == "panel" or x.get("boards")]
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(PAGE.format(dashboard=svg(m, timeline), unknown_pct=m.get('unknown_pct', 0.0),
                               timeline_note=(f"{len(snaps)} daily snapshot{'s' if len(snaps) != 1 else ''}, "
                                              f"first {snaps[0]['date']}" if snaps else "no snapshots yet")))
    print(f"{out} · {m['kept']:,} postings · {len(m['ats'])} platforms")


if __name__ == "__main__":
    main()
