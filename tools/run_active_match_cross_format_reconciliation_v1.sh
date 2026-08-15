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

if [[ "${1:-}" == "--self-test-execution-identity-guard" ]]; then
  identity_matches "integration/foundation-tranche-a-v1" "abc123" \
    "integration/foundation-tranche-a-v1" "abc123" || fail "self_test_exact_identity_rejected"
  if identity_matches "wrong" "abc123" "integration/foundation-tranche-a-v1" "abc123"; then
    fail "self_test_wrong_branch_accepted"
  fi
  if identity_matches "integration/foundation-tranche-a-v1" "wrong" \
    "integration/foundation-tranche-a-v1" "abc123"; then
    fail "self_test_wrong_head_accepted"
  fi
  echo "cross_format_reconciliation_execution_identity_guard_self_test=PASS"
  exit 0
fi

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
TMP_ROOT="${TMPDIR:-${PREFIX:-/data/data/com.termux/files/usr}/tmp}/hpfa_177_${ACTUAL_HEAD:0:12}_$$"
mkdir -p "$TMP_ROOT"
LOG="$TMP_ROOT/cross_format_reconciliation_runtime_full_v1.log"
RESULT="$TMP_ROOT/cross_format_reconciliation_result_v1.txt"
MANIFEST="$TMP_ROOT/HPFA_177_ACTIVE_MATCH_EVIDENCE_MANIFEST.json"
ZIP="$OUT/HPFA_177_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.zip"
rm -f "$ZIP"
trap 'rm -rf "$TMP_ROOT"' EXIT

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

record_post_step_failure(){
  local rc="$1" name="$2"
  [[ "$rc" -eq 0 ]] && return 0
  if [[ "$FINAL_RC" -eq 0 ]]; then
    FINAL_RC="$rc"
  fi
  if [[ -n "$FAILED_STEP" ]]; then
    FAILED_STEP="${FAILED_STEP}+${name}"
  else
    FAILED_STEP="$name"
  fi
  return 0
}

# Phone runtime is evidence execution only. Tests stay in exact-head GitHub CI.
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

python - "$TMP_ROOT" "$ACTUAL_BRANCH" "$ACTUAL_HEAD" "$ACTIVE_RESOLVED" "$FINAL_RC" "$FAILED_STEP" <<'PY'
import json, sys
from pathlib import Path

root=Path(sys.argv[1])
branch=sys.argv[2]
head=sys.argv[3]
runtime=sys.argv[4]
run_rc=int(sys.argv[5])
failed_step=sys.argv[6] or None

recon={}
labels={}
for path, target in (
    (root/"cross_format_reconciliation_lite_v1.json", "recon"),
    (root/"provider_label_value_semantics_lite_v1.json", "labels"),
):
    if path.exists():
        try:
            data=json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data={}
        if target=="recon": recon=data
        else: labels=data

totals=recon.get("reconciliation_totals") or {}
dups=recon.get("duplicate_reflection_audit") or {}
coverage=labels.get("coverage") or {}
hardening=recon.get("research_hardening") or {}
record={
    "bundle_version":"HPFA_177_ACTIVE_MATCH_EVIDENCE_V1",
    "branch":branch,
    "head_sha":head,
    "runtime_authority":runtime,
    "run_rc":run_rc,
    "failed_step":failed_step,
    "status":recon.get("status"),
    "module_status":recon.get("module_status"),
    "runtime_evidence_status":recon.get("runtime_evidence_status"),
    "active_match_evidence_pass":recon.get("active_match_evidence_pass"),
    "research_hardening_status":hardening.get("status"),
    "role_pair_count":recon.get("role_pair_count"),
    "fusion_admissibility":recon.get("fusion_admissibility"),
    "shared_id_candidate_count":totals.get("shared_id_candidate_count"),
    "exact_surface_alignment_candidate_count":totals.get("exact_surface_alignment_candidate_count"),
    "present_present_support_count":totals.get("present_present_support_count"),
    "both_missing_support_count":totals.get("both_missing_support_count"),
    "cross_id_collision_count":totals.get("cross_id_collision_count"),
    "upstream_duplicate_reflection_count":dups.get("upstream_duplicate_reflection_count"),
    "local_duplicate_candidate_count":dups.get("local_duplicate_candidate_count"),
    "action_anchor_candidate_surface_row_volume":coverage.get("action_anchor_candidate_surface_row_volume"),
    "hard_block_hits":recon.get("hard_block_hits"),
    "parse_warnings":recon.get("parse_warnings"),
    "canonical_event_count":"UNKNOWN",
    "production_release":False,
    "phone_handoff_mode":"ONE_ZIP_ONLY",
    "phone_runtime_pytest":False,
    "single_pass_upstream_refresh":True,
}
(root/"HPFA_177_ACTIVE_MATCH_EVIDENCE_MANIFEST.json").write_text(
    json.dumps(record, ensure_ascii=False, indent=2)+"\n", encoding="utf-8"
)
lines=[
    "HPFA #177 ACTIVE_MATCH RESULT",
    f"branch={branch}",
    f"head_sha={head}",
    f"run_rc={run_rc}",
    f"failed_step={failed_step or ''}",
    f"status={record['status']}",
    f"research_hardening_status={record['research_hardening_status']}",
    f"active_match_evidence_pass={record['active_match_evidence_pass']}",
    f"role_pair_count={record['role_pair_count']}",
    f"hard_block_hits={record['hard_block_hits']}",
    f"parse_warnings={record['parse_warnings']}",
    "canonical_event_count=UNKNOWN",
    "production_release=false",
]
(root/"cross_format_reconciliation_result_v1.txt").write_text(
    "\n".join(lines)+"\n", encoding="utf-8"
)
PY
POSTPROCESS_RC=$?
record_post_step_failure "$POSTPROCESS_RC" "evidence_postprocess"

if [[ "$POSTPROCESS_RC" -eq 0 ]]; then
  python - "$TMP_ROOT" "$ZIP" <<'PY'
import hashlib, json, sys, zipfile
from pathlib import Path
root=Path(sys.argv[1]); zip_path=Path(sys.argv[2])
files=[p for p in root.iterdir() if p.is_file()]
hashes={p.name:{"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"size":p.stat().st_size} for p in sorted(files)}
(root/"HPFA_177_ZIP_CONTENT_MANIFEST.json").write_text(
    json.dumps({"files":hashes}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8"
)
files=[p for p in root.iterdir() if p.is_file()]
with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED) as z:
    for p in sorted(files): z.write(p,arcname=p.name)
PY
  PACKAGING_RC=$?
  if [[ "$PACKAGING_RC" -ne 0 ]]; then
    rm -f "$ZIP"
  fi
  record_post_step_failure "$PACKAGING_RC" "evidence_bundle_packaging"
else
  rm -f "$ZIP"
fi

echo
echo "=============================="
echo "HPFA #177 KISA SONUÇ"
echo "=============================="
echo "run_rc=$FINAL_RC"
echo "failed_step=$FAILED_STEP"
if [[ -f "$RESULT" ]]; then
  grep -E '^(status|research_hardening_status|active_match_evidence_pass|role_pair_count|hard_block_hits|parse_warnings|canonical_event_count|production_release)=' "$RESULT" || true
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
