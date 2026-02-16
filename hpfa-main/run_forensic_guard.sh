#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
export PYTHONPATH="$PWD"
python -m py_compile hpfa/narrative/forensic_guard.py
python -m py_compile tests/test_forensic_guard.py
pytest -q tests/test_forensic_guard.py
