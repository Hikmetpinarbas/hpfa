#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

D="${1:-}"
if [ -z "$D" ] || [ ! -d "$D" ]; then
  echo "[FAIL] usage: hpfa_set_primary.sh /path/to/match_dir"
  exit 2
fi

export PRIMARY_DIR="$D"
echo "[OK] PRIMARY_DIR set:"
echo "$PRIMARY_DIR"
