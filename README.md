# HireSignal — a job-market warehouse

A small, end-to-end data platform over the Colombian/Spanish job market: scrape,
land raw, model a star schema in SQL, export BI-ready tables, dashboard in Metabase.

**Why it exists:** it is the same shape of work as a junior data engineer / BI analyst
role — ingestion, warehouse modelling, SQL, orchestration, tests, CI, and a dashboard
on top.

## Architecture

```
elempleo / computrabajo          pipeline/run.py
        │                              │
        ▼                              ▼
   raw JSON  ──────────────────►  warehouse.db (SQLite)
   data/raw/*.json                ├── raw_offers        (as scraped)
                                  ├── dim_country
                                  ├── dim_status
                                  ├── dim_company
                                  ├── dim_date
                                  └── fact_offer        (grain: one posting)
                                         │
                                         ▼
                                  exports/*.csv  ──► Power BI (star schema)
                                  warehouse.db   ──► Metabase (Docker, port 3033)
```

## Run it

```bash
python3 pipeline/run.py --offline   # fixture, no network — used by CI
python3 pipeline/run.py --live      # scrapes ~8 pages, takes ~1 min
```

Outputs land in `warehouse.db` and `exports/`.

## Dashboard

```bash
cd bi && docker compose up -d      # Metabase on http://localhost:3033
```
First start: create the admin user, add a **SQLite** database pointing at
`/data/warehouse.db` (mounted read-only in the compose file), then build three
questions: offers by country, offers by role family × experience band, and
applications by week.

## Power BI

`exports/*.csv` plus `bi/powerbi_measures.dax`. Load the four `dim_*` tables and
`fact_offer`, relate on the keys listed at the top of the DAX file, then paste the
measures.

## What I'd say in an interview

- The grain of the fact table is one job posting; every dimension is a `dim_` table
  with a surrogate key, so the model stays a star instead of a snowflake.
- Ingestion is idempotent: `run.py` truncates and reloads `raw_offers` from the
  JSON files, so a re-run never duplicates rows.
- Experience is parsed from the posting text, not the title, because titles lie —
  a "junior" ad asked for five years in this dataset.
- CI runs the offline path on every push, so the SQL is tested without touching
  the network.

## Status

- [x] scrapers (elempleo, computrabajo)
- [x] raw landing + idempotent load
- [x] star schema + marts in SQL
- [x] CSV export for Power BI
- [x] offline fixture + CI
- [x] live scrape: 185 postings (115 elempleo + 70 computrabajo)
- [ ] Metabase dashboard screenshots
- [ ] scheduled refresh (cron + GitHub Actions)
