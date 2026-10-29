#!/usr/bin/env python3
"""Render docs/dashboard.svg from the ATS warehouse.

    python3 dashboard/build_svg.py --db /tmp/warehouse_full.duckdb

Every number comes from the marts, so the picture cannot drift from the data.
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


def esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def text(x, y, s, size=12, fill=INK, weight="400", anchor="start", spacing=None):
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{x}" y="{y}" font-family="Inter, Segoe UI, Helvetica, Arial, sans-serif" '
            f'font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}"{ls}>{esc(s)}</text>')


def rect(x, y, w, h, fill, rx=3, stroke=None, opacity=None):
    extra = f' stroke="{stroke}" fill-opacity="{opacity}"' if stroke or opacity else ""
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"{extra}/>'


def panel(x, y, w, h, title):
    out = [rect(x, y, w, h, "#ffffff", rx=8, stroke=RULE),
           text(x + 20, y + 30, title.upper(), 10.5, MUTED, "600", spacing="1.1")]
    return out


def bars(x, y, w, rows, unit="", bar_h=22, gap=12, label_w=190, value_fmt="{:,.0f}"):
    """Horizontal bar list: label, bar, value."""
    out = []
    top = max(v for _, v in rows) or 1
    for i, (label, value) in enumerate(rows):
        yy = y + i * (bar_h + gap)
        out.append(text(x, yy + 15, str(label)[:26], 12, INK))
        bw = max(2.0, (w - label_w - 78) * value / top)
        out.append(rect(x + label_w, yy + 2, w - label_w - 78, bar_h - 6, "#eef2f5", rx=2))
        out.append(rect(x + label_w, yy + 2, bw, bar_h - 6, BARS[i % len(BARS)], rx=2))
        out.append(text(x + w, yy + 15, value_fmt.format(value) + unit, 12, MUTED, "500", "end"))
    return out


def funnel(x, y, w, stages):
    out = []
    top = stages[0][1] or 1
    for i, (label, value, note) in enumerate(stages):
        yy = y + i * 46
        bw = max(6.0, (w - 250) * value / top)
        out.append(rect(x, yy, bw, 30, BARS[min(i, len(BARS) - 1)], rx=3))
        out.append(text(x + 12, yy + 20, label, 12.5, "#ffffff" if i < 3 else INK, "600"))
        out.append(text(x + w - 130, yy + 20, f"{value:,}", 12.5, INK, "600", "end"))
        out.append(text(x + w, yy + 20, note, 11, MUTED, "400", "end"))
    return out


def kpi(x, y, w, label, value, note=""):
    return [rect(x, y, w, 74, "#f7f9fa", rx=6, stroke=RULE),
            text(x + 16, y + 26, value, 22, INK, "650"),
            text(x + 16, y + 46, label.upper(), 9.5, MUTED, "600", spacing="0.8"),
            text(x + 16, y + 63, note, 10.5, MUTED)]


def build(db: pathlib.Path, out: pathlib.Path) -> None:
    import duckdb
    con = duckdb.connect(str(db), read_only=True)

    def rows(sql):
        return con.execute(sql).fetchall()

    landed, kept, companies, with_body, no_date = rows("select * from mart_quality")[0]
    ats = rows("select ats, postings from mart_ats_share order by postings desc")
    countries = [r for r in rows("select country, postings from mart_top_countries order by postings desc")
                 if r[0] != "remote"][:8]
    roles = [("other / unclassified" if r[0] == "other" else r[0], r[1])
             for r in rows("select role_family, postings from mart_role_mix order by postings desc")]
    remote_pct = rows("select pct from mart_remote where is_remote")[0][0]
    junior = rows("select sum(junior), sum(postings) from mart_junior_share")[0]

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
         f'role="img" aria-label="Job-market harvest dashboard">',
         rect(0, 0, W, H, "#ffffff", rx=0)]

    s += [text(40, 52, "The 2026 ATS harvest", 24, INK, "650"),
          text(40, 76, "Every posting published on eleven applicant-tracking platforms, deduplicated and modelled "
                       "into a star schema.", 12.5, MUTED)]

    kpis = [("postings", f"{kept:,}", "after collapsing duplicates"),
            ("companies", f"{companies:,}", "distinct employers"),
            ("platforms", f"{len(ats)}", "ATS integrations"),
            ("fully remote", f"{remote_pct:.0f}%", "of all postings")]
    for i, (lab, val, note) in enumerate(kpis):
        s += kpi(40 + i * 282, 100, 264, lab, val, note)

    # ATS share
    s += panel(40, 200, 540, 300, "Which platform published it")
    s += bars(64, 240, 492, ats[:7], bar_h=20, gap=11)

    # countries
    s += panel(620, 200, 540, 300, "Where the jobs are")
    s += bars(644, 240, 492, countries, bar_h=20, gap=11)

    # roles
    s += panel(40, 520, 540, 300, "What the jobs are")
    s += bars(64, 560, 492, roles[:8], bar_h=20, gap=11)

    # quality funnel
    s += panel(620, 520, 540, 300, "The pipeline, in numbers")
    both = rows("select count(*) from fact_posting where description_chars >= 200 and date_key is not null")[0][0]
    s += funnel(644, 566, 492, [("landed", landed, "parquet"),
                                ("after dedupe", kept, "same requisition"),
                                ("with a real date", kept - no_date, "parsed"),
                                ("body + date", both, "fully usable") ])
    s += [text(644, 762, f"junior-titled postings: {junior[0]:,} of {junior[1]:,} "
                         f"({100 * junior[0] / max(junior[1], 1):.1f}%)", 11.5, MUTED),
          text(644, 782, "country is derived from the location string; the residual stays 'unknown', "
                         "never guessed.", 11.5, MUTED)]

    s += [f'<line x1="40" y1="{H - 52}" x2="{W - 40}" y2="{H - 52}" stroke="{RULE}"/>',
          text(40, H - 28, "HireSignal · generated from warehouse_ats.duckdb by dashboard/build_svg.py", 11, MUTED),
          text(W - 40, H - 28, "snapshot: ATS boards, October 2026", 11, MUTED, "400", "end"),
          "</svg>"]

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(s))
    print(f"{out} · {len(s)} elements")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="warehouse_ats.duckdb")
    ap.add_argument("--out", default="docs/dashboard.svg")
    a = ap.parse_args()
    db = pathlib.Path(a.db)
    if not db.exists():
        sys.exit(f"no warehouse at {db} — run pipeline/ats.py first")
    build(db, pathlib.Path(a.out))


if __name__ == "__main__":
    main()
