#!/usr/bin/env bash
# Zero-dependency demo: Python 3.10+ standard library only (sqlite3, unittest).
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
"$PY" - <<'CHECK'
import sys
assert sys.version_info >= (3, 10), f"Python 3.10+ required, found {sys.version}"
CHECK
export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"
echo "== Demo =="
"$PY" -m medallion_write_back
echo "== Tests =="
"$PY" -m unittest discover -s tests -v 2>&1 | tail -3
