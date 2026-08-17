#!/data/data/com.termux/files/usr/bin/bash
set -u -o pipefail

EXPECTED_BRANCH="${HPFA_EXPECTED_BRANCH:-}"
EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
REPO="${HPFA_REPO:-$PWD}"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"

fail(){ printf 'FAIL: %s\n' "$1" >&2; exit 2; }
origin_is_trusted(){
  local o="${1:-}"
  o="${o%/}"
  local lower="${o,,}"
  case "$lower" in
    https://github.com/hikmetpinarbas/hpfa|https://github.com/hikmetpinarbas/hpfa.git|\
git@github.com:hikmetpinarbas/hpfa|git@github.com:hikmetpinarbas/hpfa.git|\
ssh://git@github.com/hikmetpinarbas/hpfa|ssh://git@github.com/hikmetpinarbas/hpfa.git)
      return 0 ;;
    *)
      return 1 ;;
  esac
}
identity_matches(){ [[ -n "$3" && -n "$4" && "$1" == "$3" && "$2" == "$4" ]]; }

[[ -n "$EXPECTED_BRANCH" ]] || fail "expected_branch_required:set_HPFA_EXPECTED_BRANCH"
[[ -n "$EXPECTED_HEAD" ]] || fail "expected_head_required:set_HPFA_EXPECTED_HEAD"
[[ -d "$REPO" ]] || fail "product_repo_not_git_checkout:$REPO"
[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"

safe_git(){
  git -c core.fsmonitor=false -c core.hooksPath=/dev/null -c core.untrackedCache=false -C "$REPO" "$@"
}

# A clean bootstrap materializes a valid linked worktree, where .git is a file rather
# than a directory. Validate the Git worktree through Git itself so both standalone
# checkouts and linked worktrees are accepted without weakening identity checks.
INSIDE_WORK_TREE="$(safe_git rev-parse --is-inside-work-tree 2>/dev/null || true)"
[[ "$INSIDE_WORK_TREE" == "true" ]] || fail "product_repo_not_git_checkout:$REPO"
GIT_DIR_PATH="$(safe_git rev-parse --git-dir 2>/dev/null || true)"
[[ -n "$GIT_DIR_PATH" ]] || fail "product_repo_git_dir_unresolved:$REPO"

ORIGIN_URL="$(safe_git remote get-url origin 2>/dev/null || true)"
origin_is_trusted "$ORIGIN_URL" || fail "product_repo_origin_transport_or_identity_rejected:$ORIGIN_URL"
ACTUAL_BRANCH="$(safe_git branch --show-current)"
ACTUAL_HEAD="$(safe_git rev-parse HEAD)"
identity_matches "$ACTUAL_BRANCH" "$ACTUAL_HEAD" "$EXPECTED_BRANCH" "$EXPECTED_HEAD" || fail "execution_identity_mismatch:branch=$ACTUAL_BRANCH head=$ACTUAL_HEAD expected_branch=$EXPECTED_BRANCH expected_head=$EXPECTED_HEAD"
[[ -z "$(safe_git status --porcelain --untracked-files=all)" ]] || fail "product_repo_worktree_not_clean:$REPO"

ACTIVE_RESOLVED="$(cd "$ACTIVE_MATCH" && pwd -P)"
case "$ACTIVE_RESOLVED" in */runtime/active_single_match/current) ;; *) fail "active_match_runtime_authority_mismatch:$ACTIVE_RESOLVED" ;; esac
case "$OUT" in /sdcard/Download/HPFA|/storage/emulated/0/Download/HPFA) ;; */HPFA/*) fail "nested_phone_output_directory_rejected" ;; *) fail "phone_output_directory_not_allowed:$OUT" ;; esac
mkdir -p "$OUT"
rm -f "$OUT"/HPFA_183_ACTIVE_MATCH_*.zip "$OUT"/.HPFA_183_ACTIVE_MATCH_*.zip.partial

TMP_ROOT="${TMPDIR:-${PREFIX:-/data/data/com.termux/files/usr}/tmp}/hpfa_183_${ACTUAL_HEAD:0:12}_$$"
mkdir -p "$TMP_ROOT"
LOG="$TMP_ROOT/provider_metric_dictionary_runtime_full_v1.log"
RESULT="$TMP_ROOT/provider_metric_dictionary_result_v1.txt"
ZIP="$OUT/HPFA_183_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.zip"
ZIP_TMP="$OUT/.HPFA_183_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.$$.zip.partial"
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

# Runtime evidence binds the semantic dictionary to the one authoritative ACTIVE_MATCH file surface.
# It does not infer provider definitions, versions, formulas or metric values from match files.
run_step inventory python multiformat_file_inventory.py --input-root "$ACTIVE_RESOLVED" --runtime-authority "$ACTIVE_RESOLVED" --active-match-execution --out "$TMP_ROOT" || true

if [[ "$FINAL_RC" -eq 0 ]]; then
  run_step provider_metric_dictionary python provider_metric_dictionary_lite.py --repo-root "$REPO" --output "$TMP_ROOT/provider_metric_dictionary_lite_v1.json" || true
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
dictionary=read("provider_metric_dictionary_lite_v1.json")
runtime_state=inv.get("runtime_execution") or {}
hard=dictionary.get("hard_block_hits") or []
reviews=dictionary.get("review_hits") or []
supported_file_count=int(inv.get("supported_file_count") or 0)
unique_content_file_count=int(inv.get("unique_content_file_count") or 0)
inv_ok=(
    inv.get("status") == "PASS"
    and runtime_state.get("execution_status") == "ACTIVE_MATCH_EVIDENCE_PASS"
    and runtime_state.get("input_matches_runtime_authority") is True
    and supported_file_count > 0
    and unique_content_file_count > 0
)
dictionary_ok=(
    dictionary.get("status") in {"SPEC_ONLY", "REVIEW_REQUIRED"}
    and dictionary.get("spec_contract_valid") is True
    and not hard
)
execution_completed=(run_rc == 0 and inv_ok and dictionary_ok)
semantic_gate_open=bool(
    execution_completed
    and dictionary.get("downstream_provider_definition_gate_open") is True
    and dictionary.get("status") == "SPEC_ONLY"
    and not reviews
    and int(dictionary.get("provider_definition_ready_count") or 0) > 0
)
active_pass=bool(execution_completed)

legacy_dup=(inv.get("duplicate_reflection_audit") or {}).get("exact_duplicate_reflection_count")
exact_duplicate_reflection_count=dup.get("duplicate_reflection_path_count")
if exact_duplicate_reflection_count is None:
    exact_duplicate_reflection_count=dup.get("exact_duplicate_reflection_count", legacy_dup)
duplicate_reflection_group_count=dup.get("exact_duplicate_group_count")
if duplicate_reflection_group_count is None:
    duplicate_reflection_group_count=dup.get("exact_duplicate_content_group_count")

analyst_evidence={
    "surface_scope":"CURRENT_ACTIVE_MATCH_FILE_SURFACE",
    "supported_file_path_count":supported_file_count,
    "unique_content_file_count":unique_content_file_count,
    "provider_definition_ready_count":dictionary.get("provider_definition_ready_count"),
    "hpfa_domain_contract_ready_count":dictionary.get("hpfa_domain_contract_ready_count"),
    "candidate_only_metric_count":len(dictionary.get("candidate_only_metric_ids") or []),
    "open_conflict_count":dictionary.get("open_conflict_count"),
    "safe_meaning":"Provider metric semantics remain candidate/reference-only unless explicit provider definition and version admission clears; no metric value, comparison or football claim is emitted by this node.",
}

dictionary.update({
    "runtime_authority":runtime,
    "run_rc":run_rc,
    "active_match_execution_completed":execution_completed,
    "active_match_evidence_pass":active_pass,
    "runtime_evidence_status":"ACTIVE_MATCH_EVIDENCE_PASS" if active_pass else "FAIL_CLOSED",
    "provider_semantic_gate_open":semantic_gate_open,
    "analyst_evidence":analyst_evidence,
    "release_status":"NOT_PRODUCTION",
})
(root/"provider_metric_dictionary_lite_v1.json").write_text(json.dumps(dictionary,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")

record={
    "bundle_version":"HPFA_183_ACTIVE_MATCH_EVIDENCE_V1",
    "branch":branch,
    "head_sha":head,
    "runtime_authority":runtime,
    "run_rc":run_rc,
    "failed_step":failed,
    "status":dictionary.get("status") if active_pass else "FAIL_CLOSED",
    "runtime_evidence_status":"ACTIVE_MATCH_EVIDENCE_PASS" if active_pass else "FAIL_CLOSED",
    "active_match_execution_completed":execution_completed,
    "active_match_evidence_pass":active_pass,
    "provider_semantic_gate_open":semantic_gate_open,
    "spec_contract_valid":dictionary.get("spec_contract_valid"),
    "metric_record_count":dictionary.get("metric_record_count"),
    "provider_definition_ready_count":dictionary.get("provider_definition_ready_count"),
    "hpfa_domain_contract_ready_count":dictionary.get("hpfa_domain_contract_ready_count"),
    "candidate_only_metric_count":len(dictionary.get("candidate_only_metric_ids") or []),
    "open_conflict_count":dictionary.get("open_conflict_count"),
    "hard_block_hit_count":len(hard),
    "review_hit_count":len(reviews),
    "supported_file_path_count":supported_file_count,
    "unique_content_file_count":unique_content_file_count,
    "duplicate_reflection_group_count":duplicate_reflection_group_count,
    "exact_duplicate_reflection_count":exact_duplicate_reflection_count,
    "provider_candidate_is_validated_provider_identity":False,
    "provider_definition_inferred_from_active_match":False,
    "same_label_is_same_definition":False,
    "metric_value_output_allowed":False,
    "comparison_allowed":False,
    "claim_allowed":False,
    "canonical_event_count":"UNKNOWN",
    "production_release":False,
    "single_match_validation_scope":"CURRENT_ACTIVE_MATCH_ONLY",
    "phone_handoff_mode":"ONE_ZIP_ONLY",
    "phone_runtime_pytest":False,
    "active_match_binding":"INVENTORY_AUTHORITY_PLUS_PROVIDER_DICTIONARY_ADMISSION",
    "analyst_evidence":analyst_evidence,
}
(root/"HPFA_183_ACTIVE_MATCH_EVIDENCE_MANIFEST.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
lines=[
    "HPFA #183 ACTIVE_MATCH RESULT",
    f"branch={branch}", f"head_sha={head}", f"run_rc={run_rc}", f"failed_step={failed or ''}",
    f"status={record['status']}", f"active_match_evidence_pass={record['active_match_evidence_pass']}",
    f"provider_semantic_gate_open={record['provider_semantic_gate_open']}",
    f"metric_record_count={record['metric_record_count']}",
    f"provider_definition_ready_count={record['provider_definition_ready_count']}",
    f"hpfa_domain_contract_ready_count={record['hpfa_domain_contract_ready_count']}",
    f"candidate_only_metric_count={record['candidate_only_metric_count']}",
    f"open_conflict_count={record['open_conflict_count']}",
    f"review_hit_count={record['review_hit_count']}",
    f"supported_file_path_count={record['supported_file_path_count']}",
    f"unique_content_file_count={record['unique_content_file_count']}",
    f"duplicate_reflection_group_count={record['duplicate_reflection_group_count']}",
    f"exact_duplicate_reflection_count={record['exact_duplicate_reflection_count']}",
    "provider_definition_inferred_from_active_match=false",
    "metric_value_output_allowed=false", "comparison_allowed=false", "claim_allowed=false",
    "canonical_event_count=UNKNOWN", "production_release=false",
]
(root/"provider_metric_dictionary_result_v1.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
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
(root/"HPFA_183_ZIP_CONTENT_MANIFEST.json").write_text(json.dumps({"files":hashes},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
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
echo "HPFA #183 KISA SONUÇ"
echo "=============================="
echo "run_rc=$FINAL_RC"
echo "failed_step=$FAILED_STEP"
if [[ -f "$RESULT" ]]; then
  grep -E '^(status|active_match_evidence_pass|provider_semantic_gate_open|metric_record_count|provider_definition_ready_count|hpfa_domain_contract_ready_count|candidate_only_metric_count|open_conflict_count|review_hit_count|supported_file_path_count|unique_content_file_count|duplicate_reflection_group_count|exact_duplicate_reflection_count|provider_definition_inferred_from_active_match|metric_value_output_allowed|comparison_allowed|claim_allowed|canonical_event_count|production_release)=' "$RESULT" || true
else
  echo "status=FAIL_CLOSED"
  echo "active_match_evidence_pass=False"
  echo "canonical_event_count=UNKNOWN"
  echo "production_release=false"
fi
if [[ "$FINAL_RC" -eq 0 && -f "$ZIP" ]]; then echo "ZIP=$ZIP"; else echo "ZIP=NOT_CREATED"; fi
echo "=============================="
exit "$FINAL_RC"
