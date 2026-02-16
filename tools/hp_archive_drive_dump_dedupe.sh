#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
ARCH="${ARCH:-$HOME/HP_ARCHIVES/_HP_ARCHIVE_20260216_114142}"

MODE="${1:-dry}"   # dry | apply

ZIP="$(find "$ARCH" -maxdepth 1 -type f -name 'drive_dump.zip__*' | head -n 1 || true)"
DIR="$(find "$ARCH" -maxdepth 1 -type d -name 'drive_dump__*' | head -n 1 || true)"

echo "[OK] ARCH=$ARCH"
echo "[OK] mode=$MODE"
echo "[OK] zip=${ZIP:-NONE}"
echo "[OK] dir=${DIR:-NONE}"
echo

if [ -z "${ZIP:-}" ] && [ -z "${DIR:-}" ]; then
  echo "[OK] nothing to do (no drive_dump artifacts)"
  exit 0
fi

if [ -z "${ZIP:-}" ]; then
  echo "[WARN] zip not found. Not deleting extracted dir."
  exit 0
fi

echo "== ZIP HEALTHCHECK =="
if command -v unzip >/dev/null 2>&1; then
  unzip -t "$ZIP" >/dev/null
  echo "[OK] unzip -t PASS"
else
  echo "[WARN] unzip not installed; installing is recommended: pkg install unzip"
  echo "[WARN] skipping integrity test (will not delete anything in dry)"
  if [ "$MODE" = "apply" ]; then
    echo "[FAIL] refusing apply without unzip integrity test"
    exit 5
  fi
fi
echo

echo "== SIZES =="
ls -lh "$ZIP" | sed 's/^/[INFO] /'
if [ -n "${DIR:-}" ]; then
  du -sh "$DIR" | awk '{print "[INFO] " $0}'
fi
echo

if [ "$MODE" = "dry" ]; then
  echo "[DRY] would keep zip and remove extracted dir (if exists)"
  exit 0
fi

if [ "$MODE" != "apply" ]; then
  echo "[FAIL] mode must be dry|apply"
  exit 2
fi

if [ -n "${DIR:-}" ]; then
  echo "[OK] remove extracted dir: $DIR"
  rm -rf "$DIR"
else
  echo "[OK] no extracted dir to remove"
fi

echo "[OK] drive_dump dedupe complete"
