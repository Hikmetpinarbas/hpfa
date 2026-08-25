#!/data/data/com.termux/files/usr/bin/bash
set -u -o pipefail

EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
EXPECTED_REPO_SLUG="hikmetpinarbas/hpfa"
REPO="${HPFA_REPO:-$PWD}"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"

fail(){ printf 'FAIL: %s\n' "$1" >&2; exit 2; }
normalize_origin(){
  local o="${1:-}"
  o="${o%/}"; o="${o%.git}"
  o="${o#https://github.com/}"; o="${o#http://github.com/}"
  o="${o#git@github.com:}"; o="${o#ssh://git@github.com/}"
  printf '%s\n' "${o,,}"
}

[[ -n "$EXPECTED_HEAD" ]] || fail "expected_head_required:set_HPFA_EXPECTED_HEAD"
[[ -d "$REPO/.git" || -f "$REPO/.git" ]] || fail "product_repo_not_git_checkout:$REPO"
[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"

ORIGIN_URL="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"
ORIGIN_SLUG="$(normalize_origin "$ORIGIN_URL")"
ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD 2>/dev/null || true)"
[[ "$ORIGIN_SLUG" == "$EXPECTED_REPO_SLUG" ]] || fail "product_repo_origin_mismatch:$ORIGIN_URL"
[[ "$ACTUAL_HEAD" == "$EXPECTED_HEAD" ]] || fail "execution_identity_mismatch:head=$ACTUAL_HEAD expected_head=$EXPECTED_HEAD"
[[ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]] || fail "tracked_worktree_not_clean:$REPO"

ACTIVE_RESOLVED="$(cd "$ACTIVE_MATCH" && pwd -P)"
case "$ACTIVE_RESOLVED" in
  */runtime/active_single_match/current) ;;
  *) fail "active_match_runtime_authority_mismatch:$ACTIVE_RESOLVED" ;;
esac

case "$OUT" in
  /sdcard/Download/HPFA|/storage/emulated/0/Download/HPFA) ;;
  */HPFA/*) fail "nested_phone_output_directory_rejected" ;;
  *) fail "phone_output_directory_not_allowed:$OUT" ;;
esac

mkdir -p "$OUT"
LOG="${TMPDIR:-${PREFIX:-/data/data/com.termux/files/usr}/tmp}/hpfa_temporal_episode_${ACTUAL_HEAD:0:12}_$$.log"
trap 'rm -f "$LOG"' EXIT

rm -f \
  "$OUT/temporal_episode_signature_lite_v1.json" \
  "$OUT/temporal_episode_signature_lite_v1.txt" \
  "$OUT/temporal_episode_signature_analyst_audit_v1.txt"

cd "$REPO"

python active_match_full_run.py \
  --match-dir "$ACTIVE_RESOLVED" \
  --out-dir "$OUT" >"$LOG" 2>&1
FULL_RC=$?

if [[ "$FULL_RC" -ne 0 ]]; then
  echo "=== HPFA TEMPORAL EPISODE ACTIVE_MATCH CHECK ==="
  echo "head = $ACTUAL_HEAD"
  echo "full_run_rc = $FULL_RC"
  echo "temporal_run_skipped = True"
  echo "reason = UPSTREAM_FULL_RUN_FAILED"
  echo "--- upstream log tail ---"
  tail -n 80 "$LOG" || true
  echo "HPFA_TEMPORAL_EPISODE_ACTIVE_MATCH_RC=$FULL_RC"
  exit "$FULL_RC"
fi

[[ -f "$OUT/active_match_full_run_lite_v1.json" ]] || fail "full_run_output_missing_after_success"
[[ -f "$OUT/episode_feature_vector_lite_v1.json" ]] || fail "episode_feature_output_missing_after_success"

python temporal_episode_signature.py \
  --input-dir "$OUT" \
  --out-dir "$OUT" >>"$LOG" 2>&1
TEMPORAL_RC=$?

if [[ "$TEMPORAL_RC" -ne 0 || ! -f "$OUT/temporal_episode_signature_lite_v1.json" ]]; then
  echo "=== HPFA TEMPORAL EPISODE ACTIVE_MATCH CHECK ==="
  echo "head = $ACTUAL_HEAD"
  echo "full_run_rc = $FULL_RC"
  echo "temporal_run_rc = $TEMPORAL_RC"
  echo "temporal_output_present = False"
  echo "--- temporal log tail ---"
  tail -n 80 "$LOG" || true
  echo "HPFA_TEMPORAL_EPISODE_ACTIVE_MATCH_RC=$TEMPORAL_RC"
  exit "${TEMPORAL_RC:-1}"
fi

python - "$OUT" "$ACTUAL_HEAD" "$ACTIVE_RESOLVED" <<'PY'
import json, sys, zipfile
from pathlib import Path

out = Path(sys.argv[1])
head = sys.argv[2]
runtime = sys.argv[3]
full = json.loads((out / "active_match_full_run_lite_v1.json").read_text(encoding="utf-8"))
temporal = json.loads((out / "temporal_episode_signature_lite_v1.json").read_text(encoding="utf-8"))
feature = json.loads((out / "episode_feature_vector_lite_v1.json").read_text(encoding="utf-8"))

print("=== HPFA TEMPORAL EPISODE ACTIVE_MATCH CHECK ===")
print("head =", head)
print("runtime =", runtime)
print("full_run_valid =", (full.get("engineering_evidence") or {}).get("valid_run"))
print("status =", temporal.get("status"))
print("temporal_cards =", temporal.get("temporal_episode_signature_count"))
print("input_episode_cards =", temporal.get("input_episode_feature_vector_count"))
print("eligible_actions_preserved =", temporal.get("input_total_eligible_action_candidate_count"))
print("comparisons_available =", temporal.get("comparison_available_count"))
print("no_prior_in_period =", temporal.get("no_prior_episode_in_period_count"))
print("zero_duration_rate_NA =", temporal.get("zero_duration_temporal_rate_na_count"))
print("same_start_indeterminate =", temporal.get("same_start_order_indeterminate_count"))
print("unresolved =", temporal.get("unresolved_semantics_context_count"))
print("assignment_complete =", temporal.get("temporal_assignment_complete"))
print("hard_blocks =", temporal.get("hard_block_hits"))
print("review_hits =", temporal.get("review_hits"))
print("spectral_methods_applied =", temporal.get("spectral_methods_applied"))
print("recurrence_truth_applied =", temporal.get("recurrence_truth_applied"))
print("canonical_event_count =", temporal.get("canonical_event_count"))
print("production_release =", temporal.get("production_release"))

print("\n=== EN BUYUK GORUNUR BOLUM DEGISIMLERI ===")
rows = [r for r in temporal.get("temporal_episode_signatures", []) if r.get("comparison_status") == "AVAILABLE"]
rows.sort(key=lambda r: (
    -float(r.get("action_family_composition_shift_candidate") or 0.0),
    -abs(float(r.get("eligible_action_rate_delta_per_minute") or 0.0)),
    float(r.get("start_second_candidate") or 0.0),
))
for row in rows[:8]:
    print(
        row.get("start_minute_candidate"), "->", row.get("end_minute_candidate"),
        "| vs =", row.get("comparison_episode_candidate_id"),
        "| action_rate_delta =", row.get("eligible_action_rate_delta_per_minute"),
        "| composition_shift =", row.get("action_family_composition_shift_candidate"),
        "| shot_delta =", row.get("shot_rate_delta_per_minute"),
        "| turnover_delta =", row.get("turnover_rate_delta_per_minute"),
        "| recovery_delta =", row.get("recovery_rate_delta_per_minute"),
    )

zip_path = out / f"HPFA_TEMPORAL_EPISODE_ACTIVE_MATCH_{head[:7]}.zip"
files = [
    out / "temporal_episode_signature_lite_v1.json",
    out / "temporal_episode_signature_lite_v1.txt",
    out / "temporal_episode_signature_analyst_audit_v1.txt",
    out / "episode_feature_vector_lite_v1.json",
    out / "active_match_full_run_lite_v1.json",
]
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for path in files:
        if path.exists():
            z.write(path, arcname=path.name)
print("ZIP=" + str(zip_path))
PY
POST_RC=$?
if [[ "$POST_RC" -ne 0 ]]; then
  echo "HPFA_TEMPORAL_EPISODE_ACTIVE_MATCH_RC=$POST_RC"
  exit "$POST_RC"
fi

echo "HPFA_TEMPORAL_EPISODE_ACTIVE_MATCH_RC=0"
exit 0
