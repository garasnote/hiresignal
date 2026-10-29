"""One metrics dict, three sources: DuckDB, the committed JSON, or the sample.

The dashboard and the Pages site both render from this shape, so the picture on
the website and the picture in the README come from the same numbers.
"""
from __future__ import annotations

import json
import pathlib

BODY_MIN = 200


def from_duckdb(db: pathlib.Path) -> dict:
    import duckdb

    con = duckdb.connect(str(db), read_only=True)
    q = lambda sql: con.execute(sql).fetchall()  # noqa: E731

    landed, kept, companies, with_body, no_date = q("select * from mart_quality")[0]
    body_date = q("""
        select count(*) from fact_posting
        where description_chars >= 200 and date_key is not null
    """)[0][0]
    dated = q("select count(*) from fact_posting where date_key is not null")[0][0]
    remote_pct = q("select pct from mart_remote where is_remote")[0][0]
    junior, total = q("select sum(junior), sum(postings) from mart_junior_share")[0]
    out = {
        "landed": landed,
        "kept": kept,
        "companies": companies,
        "with_body": with_body,
        "no_date": no_date,
        "body_date": body_date,
        "dated": dated,
        "remote_pct": round(float(remote_pct), 1),
        "junior": junior,
        "postings": total,
        "ats": [list(r) for r in q("select ats, postings from mart_ats_share order by postings desc")],
        "countries": [list(r) for r in q(
            "select country, postings from mart_top_countries where country <> 'remote' "
            "order by postings desc")],
        "roles": [list(r) for r in q("select role_family, postings from mart_role_mix order by postings desc")],
    }
    out["unknown_pct"] = round(
        100 * next((v for k, v in out["countries"] if k == "unknown"), 0) / max(out["kept"], 1), 1)
    con.close()
    return out


def from_json(path: str | pathlib.Path) -> dict:
    return json.loads(pathlib.Path(path).read_text())


def save(metrics: dict, path: str | pathlib.Path) -> None:
    pathlib.Path(path).write_text(json.dumps(metrics, indent=1) + "\n")
