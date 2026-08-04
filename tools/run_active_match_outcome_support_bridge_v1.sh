#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="${HPFA_REPO:-/data/data/com.termux/files/home/hpfa_claim_integrity/hpfa}"
ACTIVE="${HPFA_ACTIVE_MATCH:-$REPO/runtime/active_single_match/current}"
EXPECTED_ACTIVE="${HPFA_EXPECTED_ACTIVE_MATCH:-$REPO/runtime/active_single_match/current}"
EXPECTED_BRANCH="${HPFA_EXPECTED_BRANCH:-agent/outcome-support-bridge-lite-v1}"
EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"

case "$OUT" in
  /sdcard/Download/HPFA|/storage/emulated/0/Download/HPFA) ;;
  *)
    echo "FAIL_CLOSED:nested_phone_output_directory_rejected" >&2
    echo "canonical_event_count=UNKNOWN" >&2
    echo "production_release=false" >&2
    exit 2
    ;;
esac

STATE="$OUT/outcome_support_bridge_operator_state_v1.txt"

fail() {
  local reason="$1"
  mkdir -p "$OUT" 2>/dev/null || true
  {
    echo "status=FAILED"
    echo "reason=$reason"
    echo "canonical_event_count=UNKNOWN"
    echo "production_release=false"
  } > "$STATE" 2>/dev/null || true
  echo "FAIL_CLOSED:$reason" >&2
  exit 2
}

[ "$ACTIVE" = "$EXPECTED_ACTIVE" ] || fail active_match_runtime_authority_mismatch
[ -d "$REPO/.git" ] || fail product_repo_missing
[ -d "$ACTIVE" ] || fail active_match_runtime_missing
cd "$REPO"

ACTUAL_BRANCH="$(git branch --show-current)"
ACTUAL_HEAD="$(git rev-parse HEAD)"
[ "$ACTUAL_BRANCH" = "$EXPECTED_BRANCH" ] || fail "branch_mismatch:$ACTUAL_BRANCH"
[ -n "$EXPECTED_HEAD" ] || fail expected_head_missing
[ "$ACTUAL_HEAD" = "$EXPECTED_HEAD" ] || fail "head_mismatch:$ACTUAL_HEAD"
[ -z "$(git status --porcelain --untracked-files=no)" ] || fail tracked_worktree_not_clean

resolve_input() {
  local name="$1"
  local path="$OUT/$name"
  [ -f "$path" ] || fail "input_resolution_failed:$name:0"
  printf '%s\n' "$path"
}

SELECTED_ACTION="$(resolve_input selected_action_consequence_surface_lite_v1.json)"
SELECTED_EVENT="$(resolve_input selected_event_consequence_surface_lite_v1.json)"
SEQUENCE="$(resolve_input eventonly_sequence_consequence_result_v1.json)"

mkdir -p "$OUT"
rm -f \
  "$OUT/outcome_support_bridge_lite_v1.json" \
  "$OUT/outcome_support_bridge_summary_v1.txt" \
  "$OUT/outcome_support_bridge_analyst_audit_v1.txt" \
  "$OUT/outcome_support_bridge_conflict_report_v1.json" \
  "$STATE"

set +e
python outcome_support_bridge_lite.py \
  --selected-action-consequence "$SELECTED_ACTION" \
  --selected-event-consequence "$SELECTED_EVENT" \
  --sequence-consequence "$SEQUENCE" \
  --out "$OUT"
RC=$?
set -e
[ "$RC" -eq 0 ] || fail "module_exit_code:$RC"

python - "$OUT/outcome_support_bridge_lite_v1.json" "$STATE" "$ACTUAL_HEAD" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
state = Path(sys.argv[2])
head = sys.argv[3]
if payload.get("hard_block_hits"):
    raise SystemExit("hard_blocks_present")
lines = [
    "status=COMPLETED",
    f"module_status={payload.get('status')}",
    f"runtime_code_head_sha={head}",
    f"match_surface_binding_id={payload.get('match_surface_binding_id')}",
    f"outcome_support_bridge_record_count={payload.get('outcome_support_bridge_record_count')}",
    f"outcome_support_classification_counts={payload.get('outcome_support_classification_counts')}",
    f"downstream_outcome_support_status_counts={payload.get('downstream_outcome_support_status_counts')}",
    f"conflict_record_count={payload.get('conflict_record_count')}",
    "canonical_event_count=UNKNOWN",
    "production_release=false",
]
state.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

cat "$STATE"
