#!/data/data/com.termux/files/usr/bin/bash
set -u

EXPECTED_SHA="${1:-}"
if [ -z "$EXPECTED_SHA" ]; then
  echo "usage: $0 <expected_product_commit>"
  exit 2
fi

RUNTIME="$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current"
DEST="/sdcard/Download/HPFA"
SHORT="${EXPECTED_SHA:0:7}"
LOG="$DEST/HPFA_TERMUX_CRASH_PROBE_${SHORT}.txt"
OUT="$HOME/hpfa_crash_probe_${SHORT}_$$"
SRC=""
WT=""
CHILD=""
MONITOR=""
START_TS="$(date +%s)"

mkdir -p "$DEST" "$OUT"
: > "$LOG"

log() {
  printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*" >> "$LOG"
}

checkpoint() {
  log "CHECKPOINT=$1"
  if [ -r /proc/meminfo ]; then
    awk '/MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree/ {printf "%s=%s%s ", $1, $2, $3} END {print ""}' /proc/meminfo >> "$LOG" 2>/dev/null || true
  fi
  df -h "$HOME" /sdcard 2>/dev/null | tail -n +2 >> "$LOG" || true
  sync >/dev/null 2>&1 || true
}

cleanup() {
  RC=$?
  END_TS="$(date +%s)"
  log "EXIT_RC=$RC"
  log "ELAPSED_SECONDS=$((END_TS-START_TS))"
  [ -n "$MONITOR" ] && kill "$MONITOR" >/dev/null 2>&1 || true
  [ -n "$WT" ] && [ -d "$WT" ] && git -C "$SRC" worktree remove --force "$WT" >/dev/null 2>&1 || true
  checkpoint "EXIT"
}
trap cleanup EXIT INT TERM

log "HPFA TERMUX ACTIVE_MATCH CRASH PROBE V1"
log "EXPECTED_SHA=$EXPECTED_SHA"
log "RUNTIME=$RUNTIME"
log "OUT=$OUT"
log "SHELL=$SHELL"
log "PREFIX=${PREFIX:-UNKNOWN}"
log "TERMUX_VERSION=$(termux-info 2>/dev/null | head -n 1 || echo UNKNOWN)"
log "PYTHON=$(python --version 2>&1 || true)"
log "UNAME=$(uname -a 2>/dev/null || true)"
if command -v getprop >/dev/null 2>&1; then
  log "ANDROID_RELEASE=$(getprop ro.build.version.release 2>/dev/null || true)"
  log "ANDROID_SDK=$(getprop ro.build.version.sdk 2>/dev/null || true)"
  log "DEVICE=$(getprop ro.product.model 2>/dev/null || true)"
fi
ulimit -a >> "$LOG" 2>&1 || true
checkpoint "PRE_SOURCE_DISCOVERY"

for d in "$HOME/hpfa" "$HOME/hpfa_github" "$HOME/hpfa_claim_integrity/hpfa_product" "$HOME/_hpfa-main_upstream" "$HOME/hp/repos/hpfa"; do
  [ -d "$d/.git" ] || continue
  u="$(git -C "$d" remote get-url origin 2>/dev/null || true)"
  case "$u" in
    *Hikmetpinarbas/hpfa*|*hikmetpinarbas/hpfa*)
      SRC="$d"
      break
      ;;
  esac
done

if [ -z "$SRC" ]; then
  log "FAIL=OFFICIAL_PRODUCT_CLONE_NOT_FOUND"
  exit 2
fi
log "SRC=$SRC"
checkpoint "SOURCE_FOUND"

git -C "$SRC" fetch -q origin feature/zfgv-action-grammar-synced-v1 || { log "FAIL=FETCH_FAILED"; exit 2; }
git -C "$SRC" cat-file -e "$EXPECTED_SHA^{commit}" 2>/dev/null || { log "FAIL=EXPECTED_SHA_NOT_FOUND"; exit 2; }
checkpoint "SHA_VERIFIED"

WT="$HOME/.hpfa_probe_${SHORT}_$$"
git -C "$SRC" worktree add --detach "$WT" "$EXPECTED_SHA" >> "$LOG" 2>&1 || { log "FAIL=WORKTREE_ADD_FAILED"; exit 2; }
checkpoint "WORKTREE_READY"

if [ ! -d "$RUNTIME" ]; then
  log "FAIL=ACTIVE_MATCH_RUNTIME_MISSING"
  exit 2
fi
checkpoint "ACTIVE_MATCH_PRESENT"

if command -v termux-wake-lock >/dev/null 2>&1; then
  termux-wake-lock >/dev/null 2>&1 || true
  log "WAKE_LOCK_REQUESTED=true"
else
  log "WAKE_LOCK_REQUESTED=false"
fi

log "RUNNER=$WT/active_match_exact_head_run_v1.py"
checkpoint "PRE_EXACT_HEAD_RUN"

PYTHONUNBUFFERED=1 python -u "$WT/active_match_exact_head_run_v1.py" \
  --match-dir "$RUNTIME" \
  --out-dir "$OUT" \
  --expected-product-commit "$EXPECTED_SHA" \
  >> "$LOG" 2>&1 &
CHILD=$!
log "CHILD_PID=$CHILD"

(
  while kill -0 "$CHILD" 2>/dev/null; do
    printf '%s SAMPLE ' "$(date '+%Y-%m-%dT%H:%M:%S%z')" >> "$LOG"
    if [ -r /proc/meminfo ]; then
      awk '/MemAvailable|SwapFree/ {printf "%s=%s%s ", $1, $2, $3}' /proc/meminfo >> "$LOG" 2>/dev/null || true
    fi
    if [ -r "/proc/$CHILD/status" ]; then
      awk '/VmPeak|VmSize|VmRSS|VmHWM|Threads/ {printf "%s=%s%s ", $1, $2, $3}' "/proc/$CHILD/status" >> "$LOG" 2>/dev/null || true
    else
      printf 'child_status=UNAVAILABLE ' >> "$LOG"
    fi
    if [ -r /proc/pressure/memory ]; then
      tr '\n' ' ' < /proc/pressure/memory >> "$LOG" 2>/dev/null || true
    fi
    printf '\n' >> "$LOG"
    sync >/dev/null 2>&1 || true
    sleep 2
  done
) &
MONITOR=$!

wait "$CHILD"
RC=$?
log "CHILD_RETURN_CODE=$RC"
kill "$MONITOR" >/dev/null 2>&1 || true
MONITOR=""
checkpoint "POST_EXACT_HEAD_RUN"

if [ -f "$OUT/active_match_exact_head_run_v1.json" ]; then
  cp "$OUT/active_match_exact_head_run_v1.json" "$DEST/HPFA_CRASH_PROBE_EXACT_${SHORT}.json" 2>/dev/null || true
  log "EXACT_OUTPUT_PRESENT=true"
else
  log "EXACT_OUTPUT_PRESENT=false"
fi

if command -v termux-wake-unlock >/dev/null 2>&1; then
  termux-wake-unlock >/dev/null 2>&1 || true
fi

exit "$RC"
