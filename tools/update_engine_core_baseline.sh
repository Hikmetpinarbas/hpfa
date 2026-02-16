#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
DIAG="$HOME/hpfa/_diag"
BASE="$DIAG/engine_artifacts.CORE.BASELINE.json"

RUN_DIR="${1:-}"
if [ -z "$RUN_DIR" ] || [ ! -d "$RUN_DIR" ]; then
  echo "[FAIL] usage: update_engine_core_baseline.sh /path/to/engine_run_*"
  exit 2
fi

case "$(basename "$RUN_DIR")" in
  engine_run_*) ;;
  *)
    echo "[FAIL] RUN_DIR does not look like engine_run_*: $RUN_DIR"
    exit 3
    ;;
esac

# unlock (ignore if file missing)
chmod 644 "$BASE" 2>/dev/null || true

python ~/hpfa/tools/hp_engine_artifact_guard_strict_core.py "$RUN_DIR" --write-baseline

chmod 444 "$BASE" 2>/dev/null || true

echo "[OK] core baseline update complete (locked)"
echo "[OK] BASE=$BASE"
