"""HTML rendering for the HireSignal site: real text, real history, no chart library.

Every number is text in the DOM, so it selects, copies, translates and reads
aloud. Bars are divs with a width; the only SVG left is the timeline line.

The visual language is the Sentry design system documented in DESIGN.md
(source: getdesign.md catalog, VoltAgent/awesome-design-md): violet-midnight
canvas, lime accent, Rubik.
"""
from __future__ import annotations

import html

CSS = """
/* Tokens come from DESIGN.md (Sentry). No ad-hoc colours below this line. */
:root { color-scheme: dark;
  --canvas:#150f23; --panel:#1f1633; --panel-2:#241a3d; --line:#362d59;
  --ink:#ffffff; --muted:#bdb8c0; --faint:#3f3849;
  --lime:#c2ef4e; --violet:#6a5fc1; --violet-deep:#422082;
  --r-sm:6px; --r-md:8px; --r-lg:10px; --r-xl:12px; --r-xxl:18px; }
* { box-sizing: border-box; }
html, body { background: var(--canvas); }
body { margin:0; color:var(--ink); font:16px/1.5 Rubik, -apple-system, system-ui, "Segoe UI", Helvetica, Arial, sans-serif;
       -webkit-font-smoothing: antialiased; }
a { color: var(--lime); text-decoration: none; }
a:hover { text-decoration: underline; }
.bar { display:flex; align-items:center; justify-content:space-between; gap:24px;
       max-width:1180px; margin:0 auto; padding:16px 24px; border-bottom:1px solid var(--line); }
.brand { display:inline-flex; align-items:center; gap:9px; color:var(--ink); font-weight:600; font-size:16px; }
.dot { width:8px; height:8px; border-radius:2px; background:var(--lime); }
nav.top { display:flex; gap:22px; font-size:14px; flex-wrap:wrap; }
nav.top a { color: var(--muted); }
nav.top a:hover { color: var(--lime); text-decoration:none; }
.wrap { max-width:1180px; margin:0 auto; padding:40px 24px 80px; }
.kicker { color:var(--lime); font-size:15px; font-weight:500; margin:0 0 12px; }
h1 { font-size:30px; line-height:1.2; margin:0 0 12px; font-weight:500; }
.lede { color:var(--muted); margin:0 0 32px; max-width:68ch; font-size:16px; line-height:1.7; }
.hero { display:flex; flex-wrap:wrap; align-items:flex-end; gap:16px 56px; padding-bottom:28px;
        border-bottom:1px solid var(--line); }
.big { font-size:76px; font-weight:700; letter-spacing:-.02em; line-height:1; font-variant-numeric: tabular-nums; }
.big small { display:block; font-size:14px; font-weight:400; color:var(--muted); margin-top:12px; max-width:34ch; line-height:1.5; }
.stats { display:flex; gap:44px; flex-wrap:wrap; margin:0; padding:0 0 8px; }
.stats div { min-width:88px; }
.stats dt { font-size:10px; letter-spacing:.25px; text-transform:uppercase; color:var(--muted); font-weight:600; margin:0 0 6px; }
.stats dd { margin:0; font-size:28px; font-weight:600; font-variant-numeric: tabular-nums; }
.grid { display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-top:28px; }
@media (max-width:860px) { .grid { grid-template-columns:1fr; } }
section { background:var(--panel); border:1px solid var(--line); border-radius:var(--r-xxl); padding:24px 26px 28px; }
section h2 { font-size:10px; letter-spacing:.25px; text-transform:uppercase; color:var(--muted);
             font-weight:600; margin:0; display:flex; justify-content:space-between; gap:16px; }
section h2 span { color:var(--muted); letter-spacing:0; text-transform:none; font-weight:400; font-size:12px; }
.bars { list-style:none; margin:20px 0 0; padding:0; }
.bars li { display:grid; grid-template-columns:168px 1fr 84px; align-items:center; gap:14px;
           padding:6px 0; font-variant-numeric: tabular-nums; }
.bars .label { font-size:14px; }
.bars .track { height:8px; background:#2a1f47; border-radius:var(--r-sm); overflow:hidden; }
.bars .fill { display:block; height:100%; background:var(--lime); border-radius:var(--r-sm); }
.bars .value { text-align:right; font-size:14px; color:var(--muted); }
.funnel li { grid-template-columns:150px 1fr 92px 104px; }
.funnel .pill { display:block; height:22px; border-radius:var(--r-xl); background:var(--lime); }
.funnel .name { font-size:14px; font-weight:500; }
.funnel .note { color:var(--muted); opacity:.7; font-size:12px; text-align:right; }
.timeline { margin-top:28px; }
.timeline svg { display:block; width:100%; height:auto; }
.history { margin-top:28px; }
.history ul { list-style:none; margin:18px 0 0; padding:0; display:flex; flex-wrap:wrap; gap:8px; }
.history a { display:inline-block; padding:5px 10px; border:1px solid var(--line); border-radius:4px;
             font-size:14px; color:var(--muted); font-variant-numeric: tabular-nums; }
.history a:hover { border-color:var(--lime); color:var(--lime); text-decoration:none; }
.history a[aria-current] { background:var(--lime); border-color:var(--lime); color:var(--panel); font-weight:600; }
footer { max-width:1180px; margin:0 auto; padding:0 24px 64px; color:var(--muted); font-size:14px; line-height:1.7; }
code { font-family: Monaco, Menlo, "Ubuntu Mono", monospace; font-size:13px; color:var(--lime); }
"""


def e(s) -> str:
    return html.escape(str(s))


def bars(rows, fmt="{:,.0f}"):
    top = max(v for _, v in rows) or 1
    out = []
    for name, value in rows:
        pct = 100 * value / top
        out.append(f'<li><span class="label">{e(name)}</span>'
                   f'<span class="track"><span class="fill" style="width:{pct:.1f}%"></span></span>'
                   f'<span class="value">{fmt.format(value)}</span></li>')
    return "".join(out)


def funnel(stages):
    top = stages[0][1] or 1
    out = []
    for name, value, note in stages:
        pct = 100 * value / top
        out.append(f'<li><span class="name">{e(name)}</span>'
                   f'<span class="track"><span class="pill" style="width:{max(pct, 3):.1f}%"></span></span>'
                   f'<span class="value">{value:,}</span>'
                   f'<span class="note">{e(note)}</span></li>')
    return "".join(out)


def timeline_svg(snaps, width=1132, height=110):
    if not snaps:
        return ""
    vals = [s["kept"] for s in snaps]
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or max(hi * 0.02, 1)
    lo, hi = lo - span * 0.35, hi + span * 0.35
    n = len(snaps)
    pad_l, pad_r, pad_t, pad_b = 8, 8, 24, 24
    w = width - pad_l - pad_r
    h = height - pad_t - pad_b
    pts = []
    for i, s in enumerate(snaps):
        px = pad_l + (w * i / (n - 1) if n > 1 else w / 2)
        py = pad_t + h - (h * (s["kept"] - lo) / (hi - lo))
        pts.append((px, py, s))
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py, _ in pts)
    dots = "".join(
        f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="#150f23" stroke="#c2ef4e" stroke-width="2"/>'
        f'<text x="{px:.1f}" y="{py - 12:.1f}" fill="#bdb8c0" font-size="12" text-anchor="middle">{s["kept"]:,}</text>'
        for px, py, s in pts)
    poly = (f'<polyline fill="none" stroke="#c2ef4e" stroke-width="2" stroke-linejoin="round" '
            f'stroke-linecap="round" points="{line}"/>' if n > 1 else "")
    labels = ("" if n == 1 else
              f'<text x="{pad_l}" y="{height - 6}" fill="#3f3849" font-size="12">{e(snaps[0]["date"])}</text>'
              f'<text x="{width - pad_r}" y="{height - 6}" fill="#3f3849" font-size="12" text-anchor="end">'
              f'{e(snaps[-1]["date"])}</text>')
    return (f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Postings per daily snapshot">'
            f'{poly}{dots}{labels}</svg>')


def page(*, title: str, kicker: str, h1: str, lede: str, hero_value: str, hero_note: str,
         stats, ats, countries, roles, stages, snaps, history, current: str | None,
         footer_note: str) -> str:
    hist = "".join(
        f'<li><a href="/hiresignal/{s["date"]}/"{" aria-current=page" if s["date"] == current else ""}>'
        f'{e(s["date"])} · {s["kept"]:,}</a></li>' for s in reversed(history))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(lede)[:180]}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div class="bar">
  <a class="brand" href="/hiresignal/"><span class="dot"></span>HireSignal</a>
  <nav class="top">
    <a href="https://github.com/garasnote/hiresignal">source</a>
    <a href="https://github.com/garasnote/hiresignal/blob/main/sql/ats_schema.sql">schema</a>
    <a href="https://github.com/garasnote/hiresignal/blob/main/sql/marts_ats.sql">marts</a>
    <a href="https://github.com/garasnote/rag-service">retrieval over the same corpus</a>
  </nav>
</div>
<main class="wrap">
  <p class="kicker">{e(kicker)}</p>
  <h1>{e(h1)}</h1>
  <p class="lede">{e(lede)}</p>

  <div class="hero">
    <div class="big">{e(hero_value)}<small>{e(hero_note)}</small></div>
    <dl class="stats">
      {''.join(f'<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k, v in stats)}
    </dl>
  </div>

  <div class="grid">
    <section>
      <h2>Which platform published it <span>{e(ats[0][0])} alone is {100 * ats[0][1] / max(sum(v for _, v in ats), 1):.0f}%</span></h2>
      <ul class="bars">{bars(ats[:6])}</ul>
    </section>
    <section>
      <h2>Where the jobs are <span>country parsed from location</span></h2>
      <ul class="bars">{bars(countries[:6])}</ul>
    </section>
    <section>
      <h2>What the jobs are <span>title families, lossy by design</span></h2>
      <ul class="bars">{bars([("other / unclassified" if r[0] == "other" else r[0], r[1]) for r in roles][:6])}</ul>
    </section>
    <section>
      <h2>The pipeline, in numbers <span>parquet → star schema</span></h2>
      <ul class="bars funnel">{funnel(stages)}</ul>
    </section>
  </div>

  {f'<section class="timeline"><h2>Postings over time <span>fixed {snaps[-1].get("boards", "")}-board daily panel</span></h2>{timeline_svg(snaps)}</section>' if snaps else ''}

  {f'<section class="history"><h2>Every snapshot <span>{len(history)} day{"" if len(history) == 1 else "s"}</span></h2><ul>{hist}</ul></section>' if history else ''}
</main>
<footer>{footer_note}</footer>
</body>
</html>
"""
