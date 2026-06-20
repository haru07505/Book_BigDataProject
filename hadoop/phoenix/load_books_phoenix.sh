#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

PHOENIX_ZK="${PHOENIX_ZK:-localhost:2181}"
PHOENIX_PSQL="${PHOENIX_PSQL:-psql.py}"
PHOENIX_SQLLINE="${PHOENIX_SQLLINE:-sqlline.py}"
HDFS_BOOKS_INPUT="${HDFS_BOOKS_INPUT:-/book_project/landing/books}"
HBASE_BOOKS_TABLE="${HBASE_BOOKS_TABLE:-bookbigdata:books_hbase}"
SKIP_HBASE_CREATE="${SKIP_HBASE_CREATE:-false}"
SKIP_HBASE_IMPORT="${SKIP_HBASE_IMPORT:-false}"

if [[ "$SKIP_HBASE_CREATE" == "true" ]]; then
  echo "[1/4] Skipping HBase namespace and table creation..."
else
  echo "[1/4] Creating HBase namespace and table..."
  bash "$PROJECT_ROOT/hadoop/hbase/create_books_hbase.sh"
fi

if [[ "$SKIP_HBASE_IMPORT" == "true" ]]; then
  echo "[2/4] Skipping HDFS to HBase import..."
else
  echo "[2/4] Importing HDFS data into HBase..."
  python3 "$PROJECT_ROOT/hadoop/hbase/import_books_to_hbase.py" \
    --input "$HDFS_BOOKS_INPUT" \
    --table "$HBASE_BOOKS_TABLE"
fi

echo "[3/4] Creating Phoenix view bookbigdata.books_hbase..."
"$PHOENIX_PSQL" "$PHOENIX_ZK" "$PROJECT_ROOT/hadoop/phoenix/create_books_phoenix.sql"

echo "[4/4] Running Phoenix view queries..."
"$PHOENIX_SQLLINE" "$PHOENIX_ZK" "$PROJECT_ROOT/hadoop/phoenix/phoenix_queries.sql"

echo "HBase/Phoenix load completed from HDFS input: $HDFS_BOOKS_INPUT"