"""Load raw postings + the application tracker into a small star schema, then build marts."""
import csv
import json
import pathlib
import re
import sqlite3
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB = ROOT / "warehouse.db"
EXPORTS = ROOT / "exports"
MARTS_SQL = ROOT / "sql" / "marts.sql"
DEFAULT_TRACKER = ROOT.parents[1] / "job_tracker" / "data.json"

DDL = """
CREATE TABLE IF NOT EXISTS raw_offers (
    url TEXT PRIMARY KEY, source TEXT, title TEXT, company TEXT, location TEXT,
    salary_raw TEXT, tags TEXT, scraped_at TEXT
);
CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY, date TEXT, year INTEGER, month INTEGER, week TEXT
);
CREATE TABLE IF NOT EXISTS dim_country (
    country_key INTEGER PRIMARY KEY AUTOINCREMENT, country TEXT UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS dim_role (
    role_key INTEGER PRIMARY KEY AUTOINCREMENT, family TEXT UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS dim_status (
    status_key INTEGER PRIMARY KEY AUTOINCREMENT, status TEXT UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS fact_offer (
    offer_key INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT UNIQUE, title TEXT, company TEXT,
    source TEXT, city TEXT, country_key INTEGER, role_key INTEGER,
    experience_years INTEGER, salary_min_cop INTEGER, salary_max_cop INTEGER,
    is_junior INTEGER, date_key INTEGER
);
CREATE TABLE IF NOT EXISTS fact_application (
    app_key INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT, role TEXT,
    country_key INTEGER, role_key INTEGER, status_key INTEGER, date_key INTEGER
);
"""

FAMILIES = [
    (r"(data scien|cient[ií]fic[oa] de datos|data science)", "data_science"),
    (r"(data engineer|ingenier[oa] de datos|big data|pipeline|etl)", "data_engineering"),
    (r"(machine learning|\bml\b|inteligencia artificial|\bia\b|\bai\b|llm|rag|nlp|visi[oó]n)", "ml_ai"),
    (r"(business intelligence|\bbi\b|power bi|analytics|anal[ií]tica|data analyst|analista de datos)", "bi_analytics"),
    (r"(business analyst|analista (de )?negocio|product owner)", "business_analysis"),
]
JUNIOR = re.compile(r"(junior|\bjr\b|trainee|practicante|aprendiz|reci[eé]n|sin experiencia)", re.I)


def family_of(text: str) -> str:
    t = (text or "").lower()
    for pattern, name in FAMILIES:
        if re.search(pattern, t):
            return name
    return "other"


def parse_salary_cop(raw: str):
    """'$4 a $4,5 millones' -> (4000000, 4500000); 'Salario confidencial' -> (None, None)."""
    if not raw:
        return None, None
    t = raw.lower().replace(" ", "")
    nums = re.findall(r"\$?([\d\.]+(?:,\d+)?)", t)
    vals = []
    for n in nums:
        n = n.replace(".", "").replace(",", ".")
        try:
            v = float(n)
        except ValueError:
            continue
        if "millon" in t and v < 1000:
            v *= 1_000_000
        vals.append(int(v))
    if not vals:
        return None, None
    return min(vals), max(vals)


def enrich_experience(offers, limit=0):
    """Read the 'Experiencia mínima' field from elempleo detail pages (value sits before the label)."""
    import urllib.request
    from html import unescape

    UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/124.0 Safari/537.36")
    done = 0
    for o in offers:
        if limit and done >= limit:
            break
        if o["source"] != "elempleo":
            continue
        try:
            req = urllib.request.Request(o["url"], headers={"User-Agent": UA})
            body = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
        except Exception:
            continue
        text = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", body)))
        m = re.search(r"(.{0,90})Experiencia\s*m[íi]nima", text, re.I)
        if not m:
            continue
        nums = re.findall(r"(\d{1,2})\s*a[ñn]os?", m.group(1))
        if nums:
            o["experience_years"] = int(nums[-1])
            done += 1
        elif re.search(r"sin experiencia|no requiere", m.group(1), re.I):
            o["experience_years"] = 0
            done += 1
    return offers


def date_key(value: str):
    try:
        d = datetime.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None
    return int(d.strftime("%Y%m%d"))


def _dim(cur, table: str, col: str, pk: str, value):
    if not value:
        value = "unknown"
    cur.execute(f"INSERT OR IGNORE INTO {table} ({col}) VALUES (?)", (value,))
    cur.execute(f"SELECT {pk} FROM {table} WHERE {col} = ?", (value,))
    return cur.fetchone()[0]


def load(offers, tracker_path=None, drop=True):
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.executescript(DDL)
    if drop:
        for t in ("raw_offers", "fact_offer", "fact_application", "dim_date",
                  "dim_country", "dim_role", "dim_status"):
            cur.execute(f"DELETE FROM {t}")

    for o in offers:
        cur.execute(
            "INSERT OR REPLACE INTO raw_offers VALUES (?,?,?,?,?,?,?,?)",
            (o["url"], o["source"], o.get("title", ""), o.get("company", ""),
             o.get("location", ""), o.get("salary_raw", ""), o.get("tags", ""),
             o.get("scraped_at", now_iso())),
        )
        lo, hi = parse_salary_cop(o.get("salary_raw", ""))
        family = family_of(o.get("title", ""))
        country = "Colombia" if o["source"] in ("elempleo", "computrabajo") else "Spain"
        cur.execute(
            """INSERT OR REPLACE INTO fact_offer
               (url, title, company, source, city, country_key, role_key,
                experience_years, salary_min_cop, salary_max_cop, is_junior, date_key)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (o["url"], o.get("title", ""), o.get("company", ""), o["source"],
             o.get("location", ""), _dim(cur, "dim_country", "country", "country_key", country),
             _dim(cur, "dim_role", "family", "role_key", family),
             o.get("experience_years"), lo, hi,
             1 if JUNIOR.search(o.get("title", "")) else 0,
             date_key(o.get("scraped_at"))),
        )

    tracker = pathlib.Path(tracker_path) if tracker_path else DEFAULT_TRACKER
    if tracker.exists():
        db = json.loads(tracker.read_text(encoding="utf-8"))
        for c in db.get("companies", []):
            dk = date_key(c.get("applied_date")) or date_key(c.get("created"))
            if dk:
                cur.execute("INSERT OR IGNORE INTO dim_date (date_key, date, year, month, week) "
                            "VALUES (?,?,?,?,?)",
                            (dk, str(c.get("applied_date") or c.get("created"))[:10],
                             int(str(dk)[:4]), int(str(dk)[4:6]),
                             datetime.strptime(str(dk), "%Y%m%d").strftime("%G-W%V")))
            cur.execute(
                """INSERT INTO fact_application
                   (company, role, country_key, role_key, status_key, date_key)
                   VALUES (?,?,?,?,?,?)""",
                (c.get("name", ""), c.get("role", ""),
                 _dim(cur, "dim_country", "country", "country_key", c.get("country") or "Spain"),
                 _dim(cur, "dim_role", "family", "role_key", family_of(f"{c.get('role','')} {c.get('notes','')}")),
                 _dim(cur, "dim_status", "status", "status_key", c.get("status") or "Target"),
                 dk))

    if MARTS_SQL.exists():
        cur.executescript(MARTS_SQL.read_text(encoding="utf-8"))
    con.commit()
    con.close()


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def export_marts():
    EXPORTS.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name LIKE 'mart_%'")
    written = []
    for (name,) in cur.fetchall():
        cur.execute(f"SELECT * FROM {name}")
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        with open(EXPORTS / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(rows)
        written.append((name, len(rows)))
    # star-schema tables for Power BI
    for table in ("dim_country", "dim_role", "dim_status", "dim_date", "fact_offer", "fact_application"):
        cur.execute(f"SELECT * FROM {table}")
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        with open(EXPORTS / f"{table}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(rows)
    con.close()
    return written
