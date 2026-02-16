#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
HOME_DIR="$HOME"

echo "== hp_motor dirs (top 200) =="
find "$HOME_DIR" -type d -name "hp_motor" 2>/dev/null | head -n 200

echo
echo "== HP-Motor roots that look like python projects =="
find "$HOME_DIR" -maxdepth 6 -type f \( -name "pyproject.toml" -o -name "setup.py" -o -name "setup.cfg" \) 2>/dev/null \
| grep -E "/HP-Motor|/hp-motor|HP-Motor-main" \
| head -n 200
