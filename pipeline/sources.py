"""Fetch job postings from public boards. Stdlib only, so CI needs no dependencies.

Scale: one page of a listing carries 30-64 postings, and every board paginates, so
the crawler walks pages instead of fetching one detail page per posting. That is
roughly 30x the coverage for the same number of requests.

Politeness: a small global worker pool, a per-request delay, retries with backoff,
and a hard page ceiling per term. Nothing here hammers a board.
"""
import json
import re
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html import unescape

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")

ELEMPLEO_TERMS = ["data-scientist", "machine-learning", "inteligencia-artificial",
                  "analista-de-datos", "business-intelligence", "power-bi"]

COMPUTRABAJO_TERMS = ["data-scientist", "machine-learning", "inteligencia-artificial",
                      "business-analyst"]

_DELAY = 0.15
_lock = threading.Lock()


def _get(url: str, retries: int = 2, timeout: int = 30) -> str:
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read().decode("utf-8", "replace")
            time.sleep(_DELAY)
            return body
        except Exception as exc:  # 404, 429, timeout, DNS
            last = exc
            time.sleep(_DELAY * (2 ** attempt))
    raise last


def _fetch_all(jobs, workers: int = 8) -> list:
    """jobs: list of (key, url). Returns [(key, html)] for the ones that worked."""
    def one(job):
        key, url = job
        try:
            return key, _get(url)
        except Exception:
            return key, None
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return [(k, h) for k, h in pool.map(one, jobs) if h]


def _stamp() -> str:
    with _lock:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ── elempleo (Colombia) ───────────────────────────────────────────────────────
def scrape_elempleo(terms=None, pages: int = 8, workers: int = 8) -> list:
    """Cards carry a JSON blob in data-ga4-offerdata; 64 per page."""
    terms = terms or ELEMPLEO_TERMS
    jobs = []
    for term in terms:
        for page in range(1, pages + 1):
            suffix = "" if page == 1 else f"?pagina={page}"
            jobs.append((term, f"https://www.elempleo.com/co/ofertas-empleo/trabajo-{term}{suffix}"))

    out = {}
    for _term, html in _fetch_all(jobs, workers):
        if not html:
            continue
        for m in re.finditer(r'data-ga4-offerdata="([^"]+)"', html):
            raw = m.group(1)
            head = html[max(0, m.start() - 600):m.start()]
            links = re.findall(r'data-url="([^"]+)"', head)
            if not links:
                continue
            path = links[-1]
            try:
                d = json.loads(unescape(raw))
            except json.JSONDecodeError:
                continue
            url = ("https://www.elempleo.com" + path) if path.startswith("/") else path
            out[url.split("#")[0]] = {
                "source": "elempleo",
                "title": (d.get("title") or "").strip(),
                "company": (d.get("company") or "").strip(),
                "location": (d.get("location") or "").strip(),
                "salary_raw": (d.get("salary") or "").strip(),
                "tags": (d.get("tags") or "").strip(),
                "url": url.split("#")[0],
                "scraped_at": _stamp(),
            }
    return list(out.values())


# ── technoempleo (Spain) ──────────────────────────────────────────────────────
CARD = re.compile(r'<a href="(https://www\.tecnoempleo\.com/[^"]*?rf-[0-9a-f]+)"[^>]*?class="font-weight-bold[^"]*"[^>]*?title="([^"]+)"')
CO = re.compile(r'<a title="Ofertas de Empleo ([^"]+)"')
LOC = re.compile(r'<b>([^<]+)</b>\s*(?:\((?:[^)]*)\))?[^<]*?-\s*(\d{2}/\d{2}/\d{4})')
PAY = re.compile(r'(\d{2,3}(?:\.\d{3})*\s*-\s*\d{2,3}(?:\.\d{3})*)\s*€')


def scrape_tecnoempleo(pages: int = 60, workers: int = 8) -> list:
    """The board ignores ?palabras= for anonymous clients: every query string returns
    the same listing. So this crawls the whole informática board page by page, which
    is both cheaper (one request per page instead of per term) and complete."""
    jobs = [(str(page), f"https://www.tecnoempleo.com/ofertas-trabajo/?pagina={page}")
            for page in range(1, pages + 1)]

    out = {}
    for _page, html in _fetch_all(jobs, workers):
        if not html:
            continue
        blocks = html.split('<div class="p-3 border rounded mb-3 bg-white"')[1:]
        for block in blocks:
            m = CARD.search(block)
            if not m:
                continue
            url, title = m.group(1), unescape(m.group(2)).strip()
            company = CO.search(block)
            loc = LOC.search(block)
            pay = PAY.search(block)
            out[url] = {
                "source": "tecnoempleo",
                "title": title,
                "company": unescape(company.group(1)).strip() if company else "",
                "location": unescape(loc.group(1)).strip() if loc else "",
                "salary_raw": pay.group(1) + " €" if pay else "",
                "tags": "",
                "url": url,
                "scraped_at": _stamp(),
            }
    return list(out.values())


# ── computrabajo (Colombia) ───────────────────────────────────────────────────
ANCHOR = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.S)


def scrape_computrabajo(terms=None, workers: int = 4) -> list:
    """No structured card JSON; titles come from the anchors. One page per term:
    deeper pagination returns an empty state to non-browser clients."""
    terms = terms or COMPUTRABAJO_TERMS
    jobs = [(t, f"https://co.computrabajo.com/trabajo-de-{t}") for t in terms]
    out = {}
    for _term, html in _fetch_all(jobs, workers):
        if not html:
            continue
        for href, inner in ANCHOR.findall(html):
            title = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", inner))).strip()
            if not (8 <= len(title) <= 110) or "/ofertas-de-trabajo/" not in href:
                continue
            url = href if href.startswith("http") else "https://co.computrabajo.com" + href
            out[url.split("#")[0]] = {
                "source": "computrabajo",
                "title": title,
                "company": "",
                "location": "",
                "salary_raw": "",
                "tags": "",
                "url": url.split("#")[0],
                "scraped_at": _stamp(),
            }
    return list(out.values())


def scrape_all(offline: bool = False, pages: int = 8, workers: int = 8) -> list:
    if offline:
        import pathlib
        fixture = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "sample_offers.json"
        return json.loads(fixture.read_text(encoding="utf-8"))
    offers = []
    offers += scrape_elempleo(pages=pages, workers=workers)
    offers += scrape_tecnoempleo(pages=max(pages, 40), workers=workers)
    offers += scrape_computrabajo(workers=workers)
    return offers
