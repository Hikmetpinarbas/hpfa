#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

PY="${PY:-/data/data/com.termux/files/home/hpfa/.venv/bin/python}"

~/hpfa/tools/hp_projeleri_root_guard.sh
"$PY" ~/hpfa/tools/ssot_guard_strict.py
~/hpfa/tools/hp_projeleri_drift_guard.sh

"$PY" -m hpfa.cli_engine run "$@"
