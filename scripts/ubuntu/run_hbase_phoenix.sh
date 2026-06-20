#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PHOENIX_ZK="${PHOENIX_ZK:-127.0.0.1:2181}"

bash "$PROJECT_ROOT/hadoop/phoenix/load_books_phoenix.sh"