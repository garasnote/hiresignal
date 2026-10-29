#!/usr/bin/env python3
"""Render the dashboard SVG from a metrics dict.

    python3 dashboard/build_svg.py --db warehouse_ats.duckdb
    python3 dashboard/build_svg.py --json docs/data/marts.json --out docs/dashboard.svg

Every number comes from the warehouse marts, so the picture cannot drift from the
data. No JavaScript, no chart library: the SVG is the chart. Dark by default,
because it is read on a screen, not printed.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

W = 1200
BG = "#150f23"
PANEL = "#1f1633"
RULE = "#362d59"
INK = "#ffffff"
MUTED = "#bdb8c0"
DIM = "#bdb8c0"
ACCENT = "#c2ef4e"
BARS = [ACCENT, "#45b2cf", "#3ea2bd", "#3792ac", "#30829b", "#2a738a", "#246479", "#1f5668"]
FONT = "Inter, -apple-system, Segoe UI, Helvetica, Arial, sans-serif"


def esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, size=12, fill=INK, weight="400", anchor="start", spacing=None):
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" fill="{fill}" '
            f'font-weight="{weight}" text-anchor="{anchor}"{ls}>{esc(s)}</text>')


def rect(x, y, w, h, fill, rx=4, stroke=None):
    extra = f' stroke="{stroke}"' if stroke else ""
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"{extra}/>'


def panel(x, y, w, h, title, note=""):
    out = [rect(x, y, w, h, PANEL, rx=10, stroke=RULE),
           text(x + 22, y + 32, title.upper(), 10, MUTED, "600", spacing="1.4")]
    if note:
        out.append(text(x + w - 22, y + 32, note, 10, DIM, "400", "end"))
    return out


def bars(x, y, w, rows, bar_h=26, gap=10, label_w=186, fmt="{:,.0f}"):
    out, top = [], max(v for _, v in rows) or 1
    track = w - label_w - 82
    for i, (label, value) in enumerate(rows):
        yy = y + i * (bar_h + gap)
        cy = yy + bar_h / 2
        out.append(text(x, cy + 4, str(label)[:24], 12.5, INK, "450"))
        out.append(rect(x + label_w, cy - 4, track, 8, "#2a1f47", rx=4))
        out.append(rect(x + label_w, cy - 4, max(4.0, track * value / top), 8, BARS[i % len(BARS)], rx=4))
        out.append(text(x + w, cy + 4, fmt.format(value), 12.5, MUTED, "500", "end"))
    return out


def funnel(x, y, w, stages):
    out, top = [], stages[0][1] or 1
    for i, (label, value, note) in enumerate(stages):
        yy = y + i * 44
        bw = max(8.0, (w - 250) * value / top)
        out.append(rect(x, yy, bw, 28, BARS[min(i, len(BARS) - 1)], rx=14))
        out.append(text(x + 14, yy + 19, label, 12, BG if i < 2 else INK, "600"))
        out.append(text(x + w - 128, yy + 19, f"{value:,}", 12.5, INK, "600", "end"))
        out.append(text(x + w, yy + 19, note, 10.5, DIM, "400", "end"))
    return out


def stat(x, y, value, label):
    return [text(x, y, value, 26, INK, "650"),
            text(x, y + 20, label.upper(), 9.5, MUTED, "600", spacing="1.2")]


def timeline_chart(x, y, w, h, snaps):
    vals = [s["kept"] for s in snaps]
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or max(hi * 0.02, 1)
    lo, hi = lo - span * 0.3, hi + span * 0.3
    n = len(snaps)
    pts = []
    for i, s in enumerate(snaps):
        px = x + (w * i / (n - 1) if n > 1 else w / 2)
        py = y + h - (h * (s["kept"] - lo) / (hi - lo))
        pts.append((px, py))
    out = []
    if n > 1:
        out.append(f'<polyline fill="none" stroke="{ACCENT}" stroke-width="2" stroke-linejoin="round" '
                   f'stroke-linecap="round" points="{" ".join(f"{px:.1f},{py:.1f}" for px, py in pts)}"/>')
    for (px, py), s in zip(pts, snaps):
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{BG}" stroke="{ACCENT}" stroke-width="2"/>')
        out.append(text(px, py - 14, f'{s["kept"]:,}', 11, INK, "600", "middle"))
    if n == 1:
        out.append(text(x + w / 2, y + h + 22, f'{snaps[0]["date"]} · {snaps[0]["kept"]:,} postings in the panel',
                        10.5, DIM, "400", "middle"))
    else:
        out.append(text(x, y + h + 20, snaps[0]["date"], 10.5, DIM, "500"))
        out.append(text(x + w, y + h + 20, snaps[-1]["date"], 10.5, DIM, "500", "end"))
        out.append(text(x + w / 2, y + h + 20, f'{n} snapshots · first {snaps[0]["date"]}',
                        10.5, DIM, "400", "middle"))
    return out


def svg(m: dict, timeline: dict | None = None) -> str:
    all_snaps = (timeline or {}).get("snapshots") or []
    # only the fixed panel is a time series; the whole-market snapshot is another scope
    snaps = [x for x in all_snaps if x.get("scope") == "panel" or x.get("boards")]
    h = 1090 if snaps else 880
    ats, countries, roles = m["ats"], m["countries"], m["roles"]

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" '
         f'role="img" aria-label="Job-market harvest dashboard">',
         rect(0, 0, W, h, BG, rx=0),
         f'<rect x="0" y="0" width="{W}" height="2" fill="{ACCENT}" opacity="0.55"/>']

    s += [text(48, 56, "HIRESIGNAL  ·  ATS HARVEST", 10.5, ACCENT, "700", spacing="2.4"),
          text(48, 102, "The 2026 job-market harvest", 30, INK, "650"),
          text(48, 130, "Every posting published on eleven applicant-tracking platforms, deduplicated in SQL "
                        "and modelled into a star schema.", 13, MUTED)]

    s += [text(48, 226, f"{m['kept']:,}", 64, INK, "700", spacing="-1.5"),
          text(48, 252, "postings after collapsing 11,904 duplicate listings", 12.5, MUTED)]
    s += stat(470, 196, f"{m['companies']:,}", "companies")
    s += stat(680, 196, f"{len(ats)}", "platforms")
    s += stat(870, 196, f"{m['remote_pct']:.0f}%", "fully remote")
    s += stat(1030, 196, f"{m['junior']:,}", "junior-titled")
    s += [f'<line x1="48" y1="286" x2="{W-48}" y2="286" stroke="{RULE}"/>']

    s += panel(48, 316, 540, 250, "Which platform published it",
               f"{100 * ats[0][1] / m['kept']:.0f}% from one board software")
    s += bars(70, 358, 496, [tuple(r) for r in ats[:6]], bar_h=24, gap=8)

    s += panel(612, 316, 540, 250, "Where the jobs are", "country parsed from location")
    s += bars(634, 358, 496, [tuple(r) for r in countries[:6]], bar_h=24, gap=8)

    roles_disp = [("other / unclassified" if r[0] == "other" else r[0], r[1]) for r in roles][:6]
    s += panel(48, 586, 540, 250, "What the jobs are", "title families, lossy by design")
    s += bars(70, 628, 496, roles_disp, bar_h=24, gap=8)

    s += panel(612, 586, 540, 250, "The pipeline, in numbers", "parquet → star schema")
    s += funnel(634, 626, 496, [("landed", m["landed"], "parquet"),
                                ("after dedupe", m["kept"], "same requisition"),
                                ("with a real date", m["kept"] - m["no_date"], "parsed"),
                                ("body + date", m["body_date"], "fully usable")])

    if snaps:
        s += panel(48, 856, 1104, 160, "Postings over time", f"fixed {snaps[-1].get('boards', '')}-board panel")
        s += timeline_chart(70, 918, 1060, 46, snaps)

    s += [f'<line x1="48" y1="{h - 48}" x2="{W-48}" y2="{h - 48}" stroke="{RULE}"/>',
          text(48, h - 24, "generated from the warehouse marts · never hand-edited", 10.5, DIM),
          text(W - 48, h - 24, f"snapshot: ATS boards, {m.get('as_of', 'October 2026')}", 10.5, DIM, "400", "end"),
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

    import json
    tl = pathlib.Path(a.timeline)
    timeline = json.loads(tl.read_text()) if tl.exists() else None

    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg(m, timeline))
    print(f"{out} · {len(m['ats'])} platforms · {m['kept']:,} postings")


if __name__ == "__main__":
    main()
