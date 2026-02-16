#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

echo "== 1) CANON HASH GATE =="
python tools/check_canon_hashes.py

echo "== 2) SMOKE =="
python tools/smoke_nas.py
./run_smoke.sh

echo "== 3) PYTEST =="
pytest -q

echo "CI: PASS"
