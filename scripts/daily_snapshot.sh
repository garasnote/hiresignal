#!/usr/bin/env bash
# Daily panel snapshot: fetch a fixed set of ATS boards, record one timeline point.
#
#   scripts/daily_snapshot.sh              # 1,200 boards
#   BOARDS=200 scripts/daily_snapshot.sh   # a quick run
#
# The panel is the same set every day, so the line measures drift in those boards,
# not the size of the whole market. The headline numbers come from the full
# harvest in docs/data/marts.json and only move when that is re-run.
set -euo pipefail

JOBAPP=${JOBAPP:-$HOME/Documents/JobApp}
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PY=${PY:-$HOME/.venvs/hiresignal/bin/python}
TOKENS=${TOKENS:-$JOBAPP/data/market/tokens_all.txt}
BOARDS=${BOARDS:-1200}
TIMELINE=${TIMELINE:-$REPO/docs/data/timeline.json}
DAY=${DAY:-$(date +%F)}

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

echo "[1/4] fetching $BOARDS boards"
cd "$JOBAPP"
"$PY" scripts/market_scan.py \
    --tokens-file "$TOKENS" --sample-tokens "$BOARDS" --all-roles \
    --workers 8 --out "daily_${DAY}.db" >"$TMP/scan.log" 2>&1 || { tail -25 "$TMP/scan.log"; exit 1; }
tail -3 "$TMP/scan.log"

echo "[2/4] exporting parquet"
"$PY" - "$JOBAPP/data/market/daily_${DAY}.db" "$TMP/postings.parquet" <<'PY'
import sqlite3, sys
import pyarrow as pa, pyarrow.parquet as pq
db, out = sys.argv[1], sys.argv[2]
cur = sqlite3.connect(db).execute(
    "select url,title,company,location,posted_at,ats,description from postings")
cols = [d[0] for d in cur.description]
rows = cur.fetchall()
pq.write_table(pa.table({k: [r[i] for r in rows] for i, k in enumerate(cols)}), out, compression="zstd")
print(f"{len(rows):,} rows")
PY

echo "[3/4] recording the snapshot"
cd "$REPO"
"$PY" pipeline/snapshot.py --parquet "$TMP/postings.parquet" --date "$DAY" --boards "$BOARDS" --timeline "$TIMELINE"

echo "[4/4] rebuilding the site assets"
"$PY" dashboard/build_svg.py --json docs/data/marts.json --out docs/dashboard.svg
"$PY" dashboard/build_site.py --json docs/data/marts.json --out _site

rm -f "$JOBAPP/data/market/daily_${DAY}.db"

if [ "${COMMIT:-1}" = "1" ] && [ -d "$REPO/.git" ]; then
  git add docs/data/timeline.json docs/dashboard.svg
  git -c user.name="garasnote" -c user.email="garasnote@users.noreply.github.com" \
      commit -q -m "data: snapshot ${DAY} (${BOARDS} boards)" || { echo "nothing to commit"; exit 0; }
  git push -q origin main
  echo "pushed ${DAY}"
fi
