#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
PROJ="$HOME/HP_PROJELERI"

ALLOW_FILES=(
  "pyproject.toml"
  "example_streamlit_app.py"
)

echo "[OK] scan: $PROJ (root files only)"

bad=0
while IFS= read -r f; do
  bn="$(basename "$f")"
  ok=0
  for a in "${ALLOW_FILES[@]}"; do
    [ "$bn" = "$a" ] && ok=1 && break
  done
  if [ "$ok" = "0" ]; then
    echo "[BAD] unexpected root file: $f"
    bad=1
  fi
done < <(find "$PROJ" -maxdepth 1 -type f 2>/dev/null | sort || true)

if [ "$bad" = "1" ]; then
  echo "[FAIL] HP_PROJELERI root is not clean."
  exit 11
fi

echo "[OK] HP_PROJELERI root clean."
