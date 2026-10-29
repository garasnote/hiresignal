#!/usr/bin/env python3
"""Render the dashboard SVG from a metrics dict.

    python3 dashboard/build_svg.py --db warehouse_ats.duckdb
    python3 dashboard/build_svg.py --json docs/data/marts.json --out docs/dashboard.svg

Every number comes from the warehouse marts, so the picture cannot drift from the
data. No JavaScript, no chart library: the SVG is the chart.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

W, H = 1200, 880
INK = "#1b2430"
MUTED = "#6b7787"
RULE = "#dfe4ea"
ACCENT = "#2f6f8f"
BARS = [ACCENT, "#3d7f9d", "#4b8dab", "#5a9bb8", "#6aa8c3", "#7bb4cd", "#8cc0d6", "#9dccdf"]


def esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, size=12, fill=INK, weight="400", anchor="start", spacing=None):
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{x}" y="{y}" font-family="Inter, Segoe UI, Helvetica, Arial, sans-serif" '
            f'font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}"{ls}>{esc(s)}</text>')


def rect(x, y, w, h, fill, rx=3, stroke=None):
    extra = f' stroke="{stroke}"' if stroke else ""
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"{extra}/>'


def panel(x, y, w, h, title):
    return [rect(x, y, w, h, "#ffffff", rx=8, stroke=RULE),
            text(x + 20, y + 30, title.upper(), 10.5, MUTED, "600", spacing="1.1")]


def bars(x, y, w, rows, bar_h=22, gap=12, label_w=190, fmt="{:,.0f}"):
    out, top = [], max(v for _, v in rows) or 1
    for i, (label, value) in enumerate(rows):
        yy = y + i * (bar_h + gap)
        out.append(text(x, yy + 15, str(label)[:26], 12, INK))
        out.append(rect(x + label_w, yy + 2, w - label_w - 78, bar_h - 6, "#eef2f5", rx=2))
        out.append(rect(x + label_w, yy + 2, max(2.0, (w - label_w - 78) * value / top), bar_h - 6,
                        BARS[i % len(BARS)], rx=2))
        out.append(text(x + w, yy + 15, fmt.format(value), 12, MUTED, "500", "end"))
    return out


def funnel(x, y, w, stages):
    out, top = [], stages[0][1] or 1
    for i, (label, value, note) in enumerate(stages):
        yy = y + i * 46
        out.append(rect(x, yy, max(6.0, (w - 250) * value / top), 30, BARS[min(i, len(BARS) - 1)], rx=3))
        out.append(text(x + 12, yy + 20, label, 12.5, "#ffffff" if i < 3 else INK, "600"))
        out.append(text(x + w - 130, yy + 20, f"{value:,}", 12.5, INK, "600", "end"))
        out.append(text(x + w, yy + 20, note, 11, MUTED, "400", "end"))
    return out


def kpi(x, y, w, label, value, note=""):
    return [rect(x, y, w, 74, "#f7f9fa", rx=6, stroke=RULE),
            text(x + 16, y + 26, value, 22, INK, "650"),
            text(x + 16, y + 46, label.upper(), 9.5, MUTED, "600", spacing="0.8"),
            text(x + 16, y + 63, note, 10.5, MUTED)]


def timeline_chart(x, y, w, h, snaps):
    """A line of postings per snapshot date, drawn only when there are two."""
    vals = [s["kept"] for s in snaps]
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or max(hi * 0.02, 1)
    lo, hi = lo - span * 0.25, hi + span * 0.25
    n = len(snaps)
    pts = []
    for i, s in enumerate(snaps):
        px = x + (w * i / (n - 1) if n > 1 else w / 2)
        py = y + h - (h * (s["kept"] - lo) / (hi - lo))
        pts.append((px, py))
    out = [f'<polyline fill="none" stroke="{ACCENT}" stroke-width="2.5" stroke-linejoin="round" '
           f'points="{" ".join(f"{px:.1f},{py:.1f}" for px, py in pts)}"/>']
    for (px, py), s in zip(pts, snaps):
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="{ACCENT}"/>')
        out.append(text(px, py - 12, f'{s["kept"]:,}', 10.5, MUTED, "500", "middle"))
    if n == 1:
        out.append(text(x + w / 2, y + h / 2 - 26,
                        "first snapshot — the line starts when there is a second day",
                        11, MUTED, "400", "middle"))
    out.append(text(x, y + h + 18, snaps[0]["date"], 10.5, MUTED, "500"))
    out.append(text(x + w, y + h + 18, snaps[-1]["date"], 10.5, MUTED, "500", "end"))
    out.append(text(x + w / 2, y + h + 18,
                    f'{n} snapshot' + ('s' if n != 1 else '') + f' · first {snaps[0]["date"]}',
                    10.5, MUTED, "400", "middle"))
    return out


def svg(m: dict, timeline: dict | None = None) -> str:
    all_snaps = (timeline or {}).get("snapshots") or []
    # only the fixed panel is a time series; whole-market snapshots are a different scope
    snaps = [x for x in all_snaps if x.get("scope") == "panel" or x.get("boards")]
    h = H + 200 if snaps else H
    ats, countries, roles = m["ats"], m["countries"], m["roles"]
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" '
         f'role="img" aria-label="Job-market harvest dashboard">',
         rect(0, 0, W, h, "#ffffff", rx=0)]

    s += [text(40, 52, "The 2026 ATS harvest", 24, INK, "650"),
          text(40, 76, "Every posting published on eleven applicant-tracking platforms, deduplicated "
                       "and modelled into a star schema.", 12.5, MUTED)]

    kpis = [("postings", f"{m['kept']:,}", "after collapsing duplicates"),
            ("companies", f"{m['companies']:,}", "distinct employers"),
            ("platforms", f"{len(ats)}", "ATS integrations"),
            ("fully remote", f"{m['remote_pct']:.0f}%", "of all postings")]
    for i, (lab, val, note) in enumerate(kpis):
        s += kpi(40 + i * 282, 100, 264, lab, val, note)

    s += panel(40, 200, 540, 300, "Which platform published it")
    s += bars(64, 240, 492, [tuple(r) for r in ats[:7]], bar_h=20, gap=11)
    s += panel(620, 200, 540, 300, "Where the jobs are")
    s += bars(644, 240, 492, [tuple(r) for r in countries[:8]], bar_h=20, gap=11)

    roles_disp = [("other / unclassified" if r[0] == "other" else r[0], r[1]) for r in roles][:8]
    s += panel(40, 520, 540, 300, "What the jobs are")
    s += bars(64, 560, 492, roles_disp, bar_h=20, gap=11)

    s += panel(620, 520, 540, 300, "The pipeline, in numbers")
    s += funnel(644, 566, 492, [("landed", m["landed"], "parquet"),
                                ("after dedupe", m["kept"], "same requisition"),
                                ("with a real date", m["kept"] - m["no_date"], "parsed"),
                                ("body + date", m["body_date"], "fully usable")])
    s += [text(644, 762, f"junior-titled postings: {m['junior']:,} of {m['postings']:,} "
                         f"({100 * m['junior'] / max(m['postings'], 1):.1f}%)", 11.5, MUTED),
          text(644, 782, "country is derived from the location string; the residual stays 'unknown', "
                         "never guessed.", 11.5, MUTED)]

    if snaps:
        s += panel(40, 840, 1120, 180,
                   f"Postings over time · fixed {snaps[-1].get('boards', '')}-board panel")
        s += timeline_chart(64, 884, 1072, 86, snaps)

    s += [f'<line x1="40" y1="{h - 52}" x2="{W - 40}" y2="{h - 52}" stroke="{RULE}"/>',
          text(40, h - 28, "HireSignal · generated from the warehouse marts, never hand-edited", 11, MUTED),
          text(W - 40, h - 28, f"snapshot: ATS boards, {m.get('as_of', 'October 2026')}", 11, MUTED, "400", "end"),
          "</svg>"]
    return "\n".join(s)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db")
    ap.add_argument("--json")
    ap.add_argument("--out", default="docs/dashboard.svg")
    ap.add_argument("--save-metrics")
    ap.add_argument("--timeline", default="docs/data/timeline.json")
    a = ap.parse_args()

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from dashboard.metrics import from_duckdb, from_json, save

    if a.json:
        m = from_json(a.json)
    elif a.db:
        m = from_duckdb(pathlib.Path(a.db))
    else:
        sys.exit("pass --db or --json")

    if a.save_metrics:
        save(m, a.save_metrics)
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    import json
    tl = pathlib.Path(a.timeline)
    timeline = json.loads(tl.read_text()) if tl.exists() else None
    out.write_text(svg(m, timeline))
    print(f"{out} · {len(m['ats'])} platforms · {m['kept']:,} postings")


if __name__ == "__main__":
    main()
