#!/data/data/com.termux/files/usr/bin/bash
set -u -o pipefail

EXPECTED_BRANCH="${HPFA_EXPECTED_BRANCH:-}"
EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
EXPECTED_REPO_SLUG="hikmetpinarbas/hpfa"
REPO="${HPFA_REPO:-$PWD}"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"

fail(){ printf 'FAIL: %s\n' "$1" >&2; exit 2; }
normalize_origin(){ local o="${1:-}"; o="${o%/}"; o="${o%.git}"; o="${o#https://github.com/}"; o="${o#http://github.com/}"; o="${o#git@github.com:}"; o="${o#ssh://git@github.com/}"; printf '%s\n' "${o,,}"; }
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
identity_matches "$ACTUAL_BRANCH" "$ACTUAL_HEAD" "$EXPECTED_BRANCH" "$EXPECTED_HEAD" || fail "execution_identity_mismatch:branch=$ACTUAL_BRANCH head=$ACTUAL_HEAD expected_branch=$EXPECTED_BRANCH expected_head=$EXPECTED_HEAD"
[[ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]] || fail "tracked_worktree_not_clean:$REPO"

ACTIVE_RESOLVED="$(cd "$ACTIVE_MATCH" && pwd -P)"
case "$ACTIVE_RESOLVED" in */runtime/active_single_match/current) ;; *) fail "active_match_runtime_authority_mismatch:$ACTIVE_RESOLVED" ;; esac
case "$OUT" in /sdcard/Download/HPFA|/storage/emulated/0/Download/HPFA) ;; */HPFA/*) fail "nested_phone_output_directory_rejected" ;; *) fail "phone_output_directory_not_allowed:$OUT" ;; esac
mkdir -p "$OUT"

TMP_ROOT="${TMPDIR:-${PREFIX:-/data/data/com.termux/files/usr}/tmp}/hpfa_178_${ACTUAL_HEAD:0:12}_$$"
mkdir -p "$TMP_ROOT"
LOG="$TMP_ROOT/metric_definition_policy_runtime_full_v1.log"
RESULT="$TMP_ROOT/metric_definition_policy_result_v1.txt"
MANIFEST="$TMP_ROOT/HPFA_178_ACTIVE_MATCH_EVIDENCE_MANIFEST.json"
ZIP="$OUT/HPFA_178_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.zip"
ZIP_TMP="$OUT/.HPFA_178_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.$$.zip.partial"
rm -f "$ZIP" "$ZIP_TMP"
trap 'rm -rf "$TMP_ROOT"; rm -f "$ZIP_TMP"' EXIT
trap 'exit 130' INT TERM HUP

cd "$REPO"
FINAL_RC=0
FAILED_STEP=""
run_step(){
  local name="$1"; shift
  ( printf '\n===== STEP %s =====\n' "$name"; "$@"; rc=$?; printf '===== STEP %s RC=%s =====\n' "$name" "$rc"; exit "$rc" ) >>"$LOG" 2>&1
  rc=$?
  if [[ "$rc" -ne 0 ]]; then FINAL_RC="$rc"; FAILED_STEP="$name"; return "$rc"; fi
  return 0
}
record_failure(){ local rc="$1" name="$2"; [[ "$rc" -eq 0 ]] && return 0; [[ "$FINAL_RC" -eq 0 ]] && FINAL_RC="$rc"; [[ -n "$FAILED_STEP" ]] && FAILED_STEP="${FAILED_STEP}+${name}" || FAILED_STEP="$name"; return 0; }

# Runtime binding uses the current product inventory producer; no nested full runner and no phone pytest.
run_step inventory python multiformat_file_inventory.py --input-root "$ACTIVE_RESOLVED" --runtime-authority "$ACTIVE_RESOLVED" --active-match-execution --out "$TMP_ROOT" || true

if [[ "$FINAL_RC" -eq 0 ]]; then
  python - "$REPO" "$TMP_ROOT" >>"$LOG" 2>&1 <<'PY'
import json, sys
from pathlib import Path
repo=Path(sys.argv[1]); out=Path(sys.argv[2])
sys.path.insert(0, str(repo / "hpfa/modules/core/metric_definition_policy_lite/src"))
from metric_definition_policy import write_policy_report
report=write_policy_report(repo / "configs/metrics", out)
print("metric_policy_status=" + str(report.get("status")))
print("metric_definition_candidate_count=" + str(report.get("metric_definition_candidate_count")))
print("policy_gap_count=" + str(len(report.get("policy_gaps") or [])))
if report.get("status") != "SMOKE_PASS" or (report.get("policy_gaps") or []):
    raise SystemExit(3)
PY
  POLICY_RC=$?
  record_failure "$POLICY_RC" "metric_definition_policy"
fi

python - "$TMP_ROOT" "$ACTUAL_BRANCH" "$ACTUAL_HEAD" "$ACTIVE_RESOLVED" "$FINAL_RC" "$FAILED_STEP" <<'PY'
import json, sys
from pathlib import Path
root=Path(sys.argv[1]); branch=sys.argv[2]; head=sys.argv[3]; runtime=sys.argv[4]; run_rc=int(sys.argv[5]); failed=sys.argv[6] or None

def read(name):
    p=root/name
    try: return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception: return {}
inv=read("multiformat_file_inventory_lite_v1.json")
dup=read("duplicate_file_fingerprint_report.json")
policy=read("metric_definition_policy_lite_v1.json")
runtime_state=inv.get("runtime_execution") or {}
metrics=policy.get("metrics") or []
policy_ok=policy.get("status") == "SMOKE_PASS" and not (policy.get("policy_gaps") or [])
inv_ok=inv.get("status") == "PASS" and runtime_state.get("execution_status") == "ACTIVE_MATCH_EVIDENCE_PASS" and runtime_state.get("input_matches_runtime_authority") is True
active_pass=(run_rc == 0 and policy_ok and inv_ok)
metric_states=[{
    "metric_id":m.get("metric_id"),
    "definition_fingerprint_sha256":m.get("definition_fingerprint_sha256"),
    "aggregation_class":m.get("aggregation_class"),
    "construct_validity_status":m.get("construct_validity_status"),
    "denominator_closure_status":m.get("denominator_closure_status"),
    "rate_calculation_admitted":m.get("rate_calculation_admitted"),
    "exposure_authority_status":m.get("exposure_authority_status"),
    "per90_calculation_admitted":m.get("per90_calculation_admitted"),
    "metric_value_output_allowed":m.get("metric_value_output_allowed"),
} for m in metrics]
legacy_dup=(inv.get("duplicate_reflection_audit") or {}).get("exact_duplicate_reflection_count")
exact_duplicate_reflection_count=dup.get("duplicate_reflection_path_count")
if exact_duplicate_reflection_count is None:
    exact_duplicate_reflection_count=dup.get("exact_duplicate_reflection_count", legacy_dup)
duplicate_reflection_group_count=dup.get("exact_duplicate_group_count")
if duplicate_reflection_group_count is None:
    duplicate_reflection_group_count=dup.get("exact_duplicate_content_group_count")
record={
    "bundle_version":"HPFA_178_ACTIVE_MATCH_EVIDENCE_V1",
    "branch":branch, "head_sha":head, "runtime_authority":runtime,
    "run_rc":run_rc, "failed_step":failed,
    "status":"PASS" if active_pass else "FAIL_CLOSED",
    "module_status":policy.get("status"),
    "runtime_evidence_status":"ACTIVE_MATCH_EVIDENCE_PASS" if active_pass else "FAIL_CLOSED",
    "active_match_evidence_pass":active_pass,
    "research_hardening_version":policy.get("research_hardening_version"),
    "metric_definition_candidate_count":policy.get("metric_definition_candidate_count"),
    "policy_gap_count":len(policy.get("policy_gaps") or []),
    "supported_file_path_count":inv.get("supported_file_count"),
    "unique_content_file_count":inv.get("unique_content_file_count"),
    "duplicate_reflection_group_count":duplicate_reflection_group_count,
    "exact_duplicate_reflection_count":exact_duplicate_reflection_count,
    "metric_states":metric_states,
    "validated_metric_truth":False, "construct_validity_truth":False,
    "aggregate_equivalence_truth":False, "exposure_authority_truth":False,
    "metric_value_output_allowed":False, "claim_output_allowed":False,
    "canonical_event_count":"UNKNOWN", "production_release":False,
    "phone_handoff_mode":"ONE_ZIP_ONLY", "phone_runtime_pytest":False,
    "active_match_binding":"INVENTORY_AUTHORITY_PLUS_POLICY_ADMISSION",
}
(root/"HPFA_178_ACTIVE_MATCH_EVIDENCE_MANIFEST.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
lines=[
    "HPFA #178 ACTIVE_MATCH RESULT", f"branch={branch}", f"head_sha={head}",
    f"run_rc={run_rc}", f"failed_step={failed or ''}", f"status={record['status']}",
    f"module_status={record['module_status']}", f"active_match_evidence_pass={record['active_match_evidence_pass']}",
    f"metric_definition_candidate_count={record['metric_definition_candidate_count']}", f"policy_gap_count={record['policy_gap_count']}",
    f"supported_file_path_count={record['supported_file_path_count']}", f"unique_content_file_count={record['unique_content_file_count']}",
    f"duplicate_reflection_group_count={record['duplicate_reflection_group_count']}",
    f"exact_duplicate_reflection_count={record['exact_duplicate_reflection_count']}",
    "metric_value_output_allowed=false", "construct_validity_truth=false", "exposure_authority_truth=false",
    "canonical_event_count=UNKNOWN", "production_release=false",
]
(root/"metric_definition_policy_result_v1.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
if not active_pass and run_rc == 0:
    raise SystemExit(4)
PY
POST_RC=$?
record_failure "$POST_RC" "evidence_postprocess"

if [[ "$FINAL_RC" -eq 0 ]]; then
  python - "$TMP_ROOT" "$ZIP_TMP" <<'PY'
import hashlib,json,sys,zipfile
from pathlib import Path
root=Path(sys.argv[1]); zp=Path(sys.argv[2])
files=[p for p in root.iterdir() if p.is_file()]
hashes={p.name:{"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"size":p.stat().st_size} for p in sorted(files)}
(root/"HPFA_178_ZIP_CONTENT_MANIFEST.json").write_text(json.dumps({"files":hashes},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
with zipfile.ZipFile(zp,"w",compression=zipfile.ZIP_DEFLATED) as z:
    for p in sorted(root.iterdir()):
        if p.is_file(): z.write(p,arcname=p.name)
PY
  PACK_RC=$?; record_failure "$PACK_RC" "evidence_bundle_packaging"
  if [[ "$PACK_RC" -eq 0 ]]; then
    mv -f "$ZIP_TMP" "$ZIP"; PUBLISH_RC=$?; record_failure "$PUBLISH_RC" "evidence_bundle_publish"
    [[ "$PUBLISH_RC" -eq 0 ]] || rm -f "$ZIP" "$ZIP_TMP"
  else rm -f "$ZIP" "$ZIP_TMP"; fi
else rm -f "$ZIP" "$ZIP_TMP"; fi

echo
echo "=============================="
echo "HPFA #178 KISA SONUÇ"
echo "=============================="
echo "run_rc=$FINAL_RC"
echo "failed_step=$FAILED_STEP"
if [[ -f "$RESULT" ]]; then grep -E '^(status|module_status|active_match_evidence_pass|metric_definition_candidate_count|policy_gap_count|supported_file_path_count|unique_content_file_count|duplicate_reflection_group_count|exact_duplicate_reflection_count|metric_value_output_allowed|construct_validity_truth|exposure_authority_truth|canonical_event_count|production_release)=' "$RESULT" || true; else echo "status=FAIL_CLOSED"; fi
if [[ "$FINAL_RC" -eq 0 && -f "$ZIP" ]]; then echo "ZIP=$ZIP"; else echo "ZIP=NOT_CREATED"; fi
echo "=============================="
exit "$FINAL_RC"
