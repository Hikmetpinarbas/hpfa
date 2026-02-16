#!/data/data/com.termux/files/usr/bin/bash
set -u

if [ $# -lt 1 ]; then
  echo "Usage: shortlog <command...>"
  echo "Example: shortlog python -m hpfa.cli_engine run \"$PRIMARY_DIR\" \"$OUT_DIR\" --save-meta"
  exit 2
fi

TMP="$(mktemp)"
# Komutu çalıştır, hem stdout hem stderr al
"$@" 2>&1 | tee "$TMP" >/dev/null
EC=${PIPESTATUS[0]}

echo "=== EXIT_CODE=$EC ==="
echo "=== IMPORTANT (last 80 matching lines) ==="
grep -E -i "error|fail|traceback|exception|warn|missing|no such|not found|cannot|denied" "$TMP" | tail -n 80 || true
echo "=== TAIL (last 80 lines overall) ==="
tail -n 80 "$TMP"

rm -f "$TMP"
exit $EC
