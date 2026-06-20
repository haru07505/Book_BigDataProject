#!/usr/bin/env bash
set -euo pipefail

MAX_ATTEMPTS="${HBASE_READY_ATTEMPTS:-20}"
SLEEP_SECONDS="${HBASE_READY_SLEEP_SECONDS:-5}"

run_hbase_create() {
  hbase shell -n <<'HBASE' 2>&1
status

begin
  create_namespace 'bookbigdata'
rescue => e
  raise e unless e.message.include?('NamespaceExistException') || e.message.include?('already exists')
  puts "Namespace bookbigdata already exists"
end

if exists('bookbigdata:books_hbase')
  disable 'bookbigdata:books_hbase' if is_enabled('bookbigdata:books_hbase')
  drop 'bookbigdata:books_hbase'
end

create 'bookbigdata:books_hbase', 'info', 'price', 'stat'
describe 'bookbigdata:books_hbase'
HBASE
}

for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
  set +e
  OUTPUT="$(run_hbase_create)"
  STATUS=$?
  set -e

  echo "$OUTPUT"

  if grep -Eq 'Created table bookbigdata:books_hbase|Table bookbigdata:books_hbase is ENABLED' <<< "$OUTPUT" &&
    ! grep -Eq 'ERROR|KeeperErrorCode|Traceback|NoMethodError|PleaseHoldException' <<< "$OUTPUT"; then
    exit 0
  fi

  if grep -Eq 'PleaseHoldException|Master is initializing' <<< "$OUTPUT" && [[ "$attempt" -lt "$MAX_ATTEMPTS" ]]; then
    echo "HBase Master is still initializing. Retrying in ${SLEEP_SECONDS}s (${attempt}/${MAX_ATTEMPTS})..." >&2
    sleep "$SLEEP_SECONDS"
    continue
  fi

  echo "HBase table creation failed. Check that HBase Master and RegionServer are running and hbase.rootdir/zookeeper config is correct." >&2
  exit 1
done