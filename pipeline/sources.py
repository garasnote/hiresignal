"""Fetch job postings from public boards. Stdlib only, so CI needs no dependencies."""
import json
import re
import urllib.request
from datetime import datetime, timezone
from html import unescape

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")

ELEMPLEO_TERMS = ["data-scientist", "machine-learning", "inteligencia-artificial",
                  "analista-de-datos", "business-intelligence", "power-bi"]
COMPUTRABAJO_TERMS = ["data-scientist", "machine-learning", "inteligencia-artificial",
                      "business-analyst"]


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Language": "es-CO,es;q=0.9"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", "replace")


def scrape_elempleo(terms=None) -> list:
    """elempleo embeds a JSON blob per card in data-ga4-offerdata."""
    terms = terms or ELEMPLEO_TERMS
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = {}
    for term in terms:
        try:
            html = _get(f"https://www.elempleo.com/co/ofertas-empleo/trabajo-{term}")
        except Exception:
            continue
        for m in re.finditer(r'data-url="([^"]+)"[^>]*?data-ga4-offerdata="([^"]+)"', html):
            path, raw = m.group(1), m.group(2)
            try:
                d = json.loads(unescape(raw))
            except json.JSONDecodeError:
                continue
            url = "https://www.elempleo.com" + path if path.startswith("/") else path
            out[url] = {
                "source": "elempleo",
                "title": (d.get("title") or "").strip(),
                "company": (d.get("company") or "").strip(),
                "location": (d.get("location") or "").strip(),
                "salary_raw": (d.get("salary") or "").strip(),
                "tags": (d.get("tags") or "").strip(),
                "url": url,
                "scraped_at": stamp,
            }
    return list(out.values())


ANCHOR = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.S)


def scrape_computrabajo(terms=None) -> list:
    """computrabajo has no structured card JSON; titles come from the anchors."""
    terms = terms or COMPUTRABAJO_TERMS
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = {}
    for term in terms:
        try:
            html = _get(f"https://co.computrabajo.com/trabajo-de-{term}")
        except Exception:
            continue
        for href, inner in ANCHOR.findall(html):
            title = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", inner))).strip()
            if not (8 <= len(title) <= 110) or "/ofertas-de-trabajo/" not in href:
                continue
            url = href if href.startswith("http") else "https://co.computrabajo.com" + href
            out[url] = {
                "source": "computrabajo",
                "title": title,
                "company": "",
                "location": "",
                "salary_raw": "",
                "tags": "",
                "url": url.split("#")[0],
                "scraped_at": stamp,
            }
    return list(out.values())


def scrape_all(offline: bool = False) -> list:
    if offline:
        import pathlib
        fixture = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "sample_offers.json"
        return json.loads(fixture.read_text(encoding="utf-8"))
    return scrape_elempleo() + scrape_computrabajo()
