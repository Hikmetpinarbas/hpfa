#!/data/data/com.termux/files/usr/bin/bash
set -u -o pipefail

EXPECTED_BRANCH="${HPFA_EXPECTED_BRANCH:-}"
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
identity_matches(){ [[ -n "$3" && -n "$4" && "$1" == "$3" && "$2" == "$4" ]]; }

[[ -n "$EXPECTED_BRANCH" ]] || fail "expected_branch_required:set_HPFA_EXPECTED_BRANCH"
[[ -n "$EXPECTED_HEAD" ]] || fail "expected_head_required:set_HPFA_EXPECTED_HEAD"
[[ -d "$REPO/.git" ]] || fail "product_repo_not_git_checkout:$REPO"
[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"

ORIGIN_URL="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"
ORIGIN_SLUG="$(normalize_origin "$ORIGIN_URL")"
ACTUAL_BRANCH="$(git -C "$REPO" branch --show-current)"
ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"
[[ "$ORIGIN_SLUG" == "$EXPECTED_REPO_SLUG" ]] || fail "product_repo_origin_mismatch:$ORIGIN_URL"
identity_matches "$ACTUAL_BRANCH" "$ACTUAL_HEAD" "$EXPECTED_BRANCH" "$EXPECTED_HEAD" || \
  fail "execution_identity_mismatch:branch=$ACTUAL_BRANCH head=$ACTUAL_HEAD expected_branch=$EXPECTED_BRANCH expected_head=$EXPECTED_HEAD"
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
# ONE_ZIP_ONLY: remove stale #181 final/partial bundles before the current run.
rm -f "$OUT"/HPFA_181_ACTIVE_MATCH_*.zip "$OUT"/.HPFA_181_ACTIVE_MATCH_*.zip.partial

TMP_ROOT="${TMPDIR:-${PREFIX:-/data/data/com.termux/files/usr}/tmp}/hpfa_181_${ACTUAL_HEAD:0:12}_$$"
mkdir -p "$TMP_ROOT"
LOG="$TMP_ROOT/aggregate_definition_alignment_runtime_full_v1.log"
RESULT="$TMP_ROOT/aggregate_definition_alignment_result_v1.txt"
ZIP="$OUT/HPFA_181_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.zip"
ZIP_TMP="$OUT/.HPFA_181_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.$$.zip.partial"
rm -f "$ZIP" "$ZIP_TMP"
trap 'rm -rf "$TMP_ROOT"; rm -f "$ZIP_TMP"' EXIT
trap 'exit 130' INT TERM HUP

cd "$REPO"
FINAL_RC=0
FAILED_STEP=""

run_step(){
  local name="$1"; shift
  (
    printf '\n===== STEP %s =====\n' "$name"
    "$@"
    rc=$?
    printf '===== STEP %s RC=%s =====\n' "$name" "$rc"
    exit "$rc"
  ) >>"$LOG" 2>&1
  rc=$?
  if [[ "$rc" -ne 0 ]]; then
    FINAL_RC="$rc"
    FAILED_STEP="$name"
    return "$rc"
  fi
  return 0
}

record_failure(){
  local rc="$1" name="$2"
  [[ "$rc" -eq 0 ]] && return 0
  [[ "$FINAL_RC" -eq 0 ]] && FINAL_RC="$rc"
  if [[ -n "$FAILED_STEP" ]]; then
    FAILED_STEP="${FAILED_STEP}+${name}"
  else
    FAILED_STEP="$name"
  fi
  return 0
}

# Single-pass upstream refresh. Phone runtime is evidence execution only; tests stay in GitHub CI.
run_step inventory \
  python multiformat_file_inventory.py \
    --input-root "$ACTIVE_RESOLVED" \
    --runtime-authority "$ACTIVE_RESOLVED" \
    --active-match-execution \
    --out "$TMP_ROOT" || true

if [[ "$FINAL_RC" -eq 0 ]]; then
  run_step csv \
    python csv_surface_reader_lite.py \
      --input-root "$ACTIVE_RESOLVED" \
      --inventory "$TMP_ROOT/multiformat_file_inventory_lite_v1.json" \
      --out "$TMP_ROOT" || true
fi

if [[ "$FINAL_RC" -eq 0 ]]; then
  run_step xlsx \
    python xlsx_surface_reader_lite.py \
      --input-root "$ACTIVE_RESOLVED" \
      --inventory "$TMP_ROOT/multiformat_file_inventory_lite_v1.json" \
      --out "$TMP_ROOT" || true
fi

if [[ "$FINAL_RC" -eq 0 ]]; then
  run_step xml \
    python xml_surface_reader_lite.py \
      --input-root "$ACTIVE_RESOLVED" \
      --inventory "$TMP_ROOT/multiformat_file_inventory_lite_v1.json" \
      --out "$TMP_ROOT" || true
fi

if [[ "$FINAL_RC" -eq 0 ]]; then
  run_step field_semantics \
    python provider_alias_field_semantics_lite.py \
      --input-root "$ACTIVE_RESOLVED" \
      --csv-audit "$TMP_ROOT/csv_surface_audit_lite_v1.json" \
      --xlsx-audit "$TMP_ROOT/xlsx_surface_audit_lite_v1.json" \
      --xml-audit "$TMP_ROOT/xml_surface_audit_lite_v1.json" \
      --out "$TMP_ROOT" || true
fi

if [[ "$FINAL_RC" -eq 0 ]]; then
  run_step label_value_semantics \
    python provider_label_value_semantics_lite.py \
      --runtime-authority "$ACTIVE_RESOLVED" \
      --expected-runtime-authority "$ACTIVE_RESOLVED" \
      --csv-audit "$TMP_ROOT/csv_surface_audit_lite_v1.json" \
      --xlsx-audit "$TMP_ROOT/xlsx_surface_audit_lite_v1.json" \
      --xml-audit "$TMP_ROOT/xml_surface_audit_lite_v1.json" \
      --field-semantics "$TMP_ROOT/provider_alias_field_semantics_lite_v1.json" \
      --registry "$REPO/hpfa/modules/core/provider_label_value_semantics_lite/registry/sportsbase_label_semantics_seed_v1.json" \
      --out "$TMP_ROOT" || true
fi

if [[ "$FINAL_RC" -eq 0 ]]; then
  run_step reconciliation \
    python cross_format_reconciliation_lite.py \
      --input-root "$ACTIVE_RESOLVED" \
      --expected-runtime-authority "$ACTIVE_RESOLVED" \
      --inventory "$TMP_ROOT/multiformat_file_inventory_lite_v1.json" \
      --csv-audit "$TMP_ROOT/csv_surface_audit_lite_v1.json" \
      --xlsx-audit "$TMP_ROOT/xlsx_surface_audit_lite_v1.json" \
      --xml-audit "$TMP_ROOT/xml_surface_audit_lite_v1.json" \
      --field-semantics "$TMP_ROOT/provider_alias_field_semantics_lite_v1.json" \
      --label-semantics "$TMP_ROOT/provider_label_value_semantics_lite_v1.json" \
      --xml-group-registry "$REPO/hpfa/modules/core/cross_format_reconciliation_lite/registry/sportsbase_xml_group_semantics_v1.json" \
      --out "$TMP_ROOT" || true
fi

if [[ "$FINAL_RC" -eq 0 ]]; then
  run_step metric_definition_policy \
    python - "$REPO" "$TMP_ROOT" <<'PY' || true
import sys
from pathlib import Path
repo=Path(sys.argv[1]); out=Path(sys.argv[2])
sys.path.insert(0, str(repo / "hpfa/modules/core/metric_definition_policy_lite/src"))
from metric_definition_policy import write_policy_report
report=write_policy_report(repo / "configs/metrics", out)
print("metric_policy_status=" + str(report.get("status")))
print("policy_gap_count=" + str(len(report.get("policy_gaps") or [])))
if report.get("status") not in {"SMOKE_PASS", "REVIEW_REQUIRED"}:
    raise SystemExit(3)
PY
fi

if [[ "$FINAL_RC" -eq 0 ]]; then
  run_step aggregate_definition_alignment \
    python aggregate_definition_alignment_lite.py \
      --xlsx-audit "$TMP_ROOT/xlsx_surface_audit_lite_v1.json" \
      --label-semantics "$TMP_ROOT/provider_label_value_semantics_lite_v1.json" \
      --reconciliation "$TMP_ROOT/cross_format_reconciliation_lite_v1.json" \
      --metric-policy "$TMP_ROOT/metric_definition_policy_lite_v1.json" \
      --registry "$REPO/hpfa/modules/core/aggregate_definition_alignment_lite/registry/sportsbase_aggregate_definition_candidates_v1.json" \
      --output "$TMP_ROOT/aggregate_definition_alignment_lite_v1.json" || true
fi

python - "$TMP_ROOT" "$ACTUAL_BRANCH" "$ACTUAL_HEAD" "$ACTIVE_RESOLVED" "$FINAL_RC" "$FAILED_STEP" <<'PY'
import json, sys
from pathlib import Path
root=Path(sys.argv[1]); branch=sys.argv[2]; head=sys.argv[3]; runtime=sys.argv[4]
run_rc=int(sys.argv[5]); failed=sys.argv[6] or None

def read(name):
    p=root/name
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}

inv=read("multiformat_file_inventory_lite_v1.json")
dup=read("duplicate_file_fingerprint_report.json")
align=read("aggregate_definition_alignment_lite_v1.json")
runtime_state=inv.get("runtime_execution") or {}
hard=align.get("hard_block_hits") or []
reviews=align.get("review_hits") or []
inv_ok=(
    inv.get("status") == "PASS"
    and runtime_state.get("execution_status") == "ACTIVE_MATCH_EVIDENCE_PASS"
    and runtime_state.get("input_matches_runtime_authority") is True
)
execution_completed=(
    run_rc == 0
    and inv_ok
    and align.get("status") in {"SMOKE_PASS", "REVIEW_REQUIRED"}
    and not hard
)
definition_cleared=(
    execution_completed
    and align.get("status") == "SMOKE_PASS"
    and not reviews
)
downstream_gate_open=bool(execution_completed and definition_cleared)
codes=[str(item.get("code")) for item in reviews]
align.update({
    "runtime_authority":runtime,
    "run_rc":run_rc,
    "active_match_execution_completed":execution_completed,
    "active_match_evidence_pass":execution_completed,
    "definition_alignment_cleared":definition_cleared,
    "downstream_gate_open":downstream_gate_open,
    "runtime_evidence_status":"ACTIVE_MATCH_EXECUTION_COMPLETED" if execution_completed else "FAIL_CLOSED",
    "release_status":"NOT_PRODUCTION",
})
(root/"aggregate_definition_alignment_lite_v1.json").write_text(
    json.dumps(align, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8"
)
record={
    "bundle_version":"HPFA_181_ACTIVE_MATCH_EVIDENCE_V1",
    "branch":branch,
    "head_sha":head,
    "runtime_authority":runtime,
    "run_rc":run_rc,
    "failed_step":failed,
    "status":align.get("status") if execution_completed else "FAIL_CLOSED",
    "runtime_evidence_status":"ACTIVE_MATCH_EXECUTION_COMPLETED" if execution_completed else "FAIL_CLOSED",
    "active_match_execution_completed":execution_completed,
    "active_match_evidence_pass":execution_completed,
    "definition_alignment_cleared":definition_cleared,
    "downstream_gate_open":downstream_gate_open,
    "definition_candidate_count":align.get("definition_candidate_count"),
    "alignment_decision_counts":align.get("alignment_decision_counts"),
    "hard_block_hit_count":len(hard),
    "review_hit_count":len(reviews),
    "provider_definition_review_count":codes.count("provider_definition_evidence_unresolved"),
    "denominator_closure_review_count":codes.count("metric_denominator_closure_unresolved"),
    "duplicate_reflection_group_count":dup.get("exact_duplicate_group_count"),
    "exact_duplicate_reflection_count":dup.get("duplicate_reflection_path_count", dup.get("exact_duplicate_reflection_count")),
    "source_role_separation_required":align.get("source_role_separation_required"),
    "xlsx_row_is_event_identity":False,
    "csv_xml_candidate_linkage_is_physical_event_identity":False,
    "aggregate_equivalence_truth":False,
    "measurement_invariance_truth":False,
    "comparison_allowed":False,
    "metric_value_output_allowed":False,
    "claim_allowed":False,
    "canonical_event_count":"UNKNOWN",
    "production_release":False,
    "single_match_validation_scope":"CURRENT_ACTIVE_MATCH_ONLY",
    "phone_handoff_mode":"ONE_ZIP_ONLY",
    "phone_runtime_pytest":False,
    "single_pass_upstream_refresh":True,
}
(root/"HPFA_181_ACTIVE_MATCH_EVIDENCE_MANIFEST.json").write_text(
    json.dumps(record, ensure_ascii=False, indent=2)+"\n", encoding="utf-8"
)
lines=[
    "HPFA #181 ACTIVE_MATCH RESULT",
    f"branch={branch}",
    f"head_sha={head}",
    f"run_rc={run_rc}",
    f"failed_step={failed or ''}",
    f"status={record['status']}",
    f"active_match_evidence_pass={record['active_match_evidence_pass']}",
    f"definition_alignment_cleared={record['definition_alignment_cleared']}",
    f"downstream_gate_open={record['downstream_gate_open']}",
    f"definition_candidate_count={record['definition_candidate_count']}",
    f"review_hit_count={record['review_hit_count']}",
    f"provider_definition_review_count={record['provider_definition_review_count']}",
    f"denominator_closure_review_count={record['denominator_closure_review_count']}",
    f"duplicate_reflection_group_count={record['duplicate_reflection_group_count']}",
    f"exact_duplicate_reflection_count={record['exact_duplicate_reflection_count']}",
    "aggregate_equivalence_truth=false",
    "measurement_invariance_truth=false",
    "comparison_allowed=false",
    "metric_value_output_allowed=false",
    "canonical_event_count=UNKNOWN",
    "production_release=false",
]
(root/"aggregate_definition_alignment_result_v1.txt").write_text(
    "\n".join(lines)+"\n", encoding="utf-8"
)
if not execution_completed and run_rc == 0:
    raise SystemExit(4)
PY
POST_RC=$?
record_failure "$POST_RC" "evidence_postprocess"

if [[ "$FINAL_RC" -eq 0 ]]; then
  python - "$TMP_ROOT" "$ZIP_TMP" <<'PY'
import hashlib, json, sys, zipfile
from pathlib import Path
root=Path(sys.argv[1]); zip_path=Path(sys.argv[2])
files=[p for p in root.iterdir() if p.is_file()]
hashes={
    p.name:{"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"size":p.stat().st_size}
    for p in sorted(files)
}
(root/"HPFA_181_ZIP_CONTENT_MANIFEST.json").write_text(
    json.dumps({"files":hashes}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8"
)
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for p in sorted(root.iterdir()):
        if p.is_file():
            z.write(p, arcname=p.name)
PY
  PACK_RC=$?
  record_failure "$PACK_RC" "evidence_bundle_packaging"
  if [[ "$PACK_RC" -eq 0 ]]; then
    mv -f "$ZIP_TMP" "$ZIP"
    PUBLISH_RC=$?
    record_failure "$PUBLISH_RC" "evidence_bundle_publish"
    [[ "$PUBLISH_RC" -eq 0 ]] || rm -f "$ZIP" "$ZIP_TMP"
  else
    rm -f "$ZIP" "$ZIP_TMP"
  fi
else
  rm -f "$ZIP" "$ZIP_TMP"
fi

echo
echo "=============================="
echo "HPFA #181 KISA SONUÇ"
echo "=============================="
echo "run_rc=$FINAL_RC"
echo "failed_step=$FAILED_STEP"
if [[ -f "$RESULT" ]]; then
  grep -E '^(status|active_match_evidence_pass|definition_alignment_cleared|downstream_gate_open|definition_candidate_count|review_hit_count|provider_definition_review_count|denominator_closure_review_count|duplicate_reflection_group_count|exact_duplicate_reflection_count|aggregate_equivalence_truth|measurement_invariance_truth|comparison_allowed|metric_value_output_allowed|canonical_event_count|production_release)=' "$RESULT" || true
else
  echo "status=FAIL_CLOSED"
  echo "active_match_evidence_pass=False"
  echo "canonical_event_count=UNKNOWN"
  echo "production_release=false"
fi
if [[ "$FINAL_RC" -eq 0 && -f "$ZIP" ]]; then
  echo "ZIP=$ZIP"
else
  echo "ZIP=NOT_CREATED"
fi
echo "=============================="

exit "$FINAL_RC"
