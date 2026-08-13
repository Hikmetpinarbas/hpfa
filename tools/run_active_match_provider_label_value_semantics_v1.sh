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
  echo "provider_label_value_semantics_execution_identity_guard_self_test=PASS"
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
TMP_ROOT="${TMPDIR:-${PREFIX:-/data/data/com.termux/files/usr}/tmp}/hpfa_175_${ACTUAL_HEAD:0:12}_$$"
mkdir -p "$TMP_ROOT"
LOG="$TMP_ROOT/provider_label_value_semantics_runtime_full_v1.log"
RESULT="$TMP_ROOT/provider_label_value_semantics_result_v1.txt"
MANIFEST="$TMP_ROOT/HPFA_175_ACTIVE_MATCH_EVIDENCE_MANIFEST.json"
ZIP="$OUT/HPFA_175_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.zip"
rm -f "$ZIP"
trap 'rm -rf "$TMP_ROOT"' EXIT

cd "$REPO"

FINAL_RC=0
FAILED_STEP=""

run_step(){
  local name="$1"; shift
  {
    printf '\n===== STEP %s =====\n' "$name"
    "$@"
    rc=$?
    printf '===== STEP %s RC=%s =====\n' "$name" "$rc"
    exit "$rc"
  } >>"$LOG" 2>&1
  rc=$?
  if [[ "$rc" -ne 0 ]]; then
    FINAL_RC="$rc"
    FAILED_STEP="$name"
    return "$rc"
  fi
  return 0
}

# Phone runtime is execution evidence, not a second CI system.
# Tests stay in exact-head GitHub CI. Runtime refreshes each producer once.
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

python - "$TMP_ROOT" "$ACTUAL_BRANCH" "$ACTUAL_HEAD" "$ACTIVE_RESOLVED" "$FINAL_RC" "$FAILED_STEP" <<'PY'
import hashlib, json, sys
from pathlib import Path

root=Path(sys.argv[1])
branch=sys.argv[2]
head=sys.argv[3]
runtime=sys.argv[4]
run_rc=int(sys.argv[5])
failed_step=sys.argv[6] or None

main=root/"provider_label_value_semantics_lite_v1.json"
payload={}
if main.exists():
    try:
        payload=json.loads(main.read_text(encoding="utf-8"))
    except Exception:
        payload={}

coverage=payload.get("coverage") or {}
record={
    "bundle_version":"HPFA_175_ACTIVE_MATCH_EVIDENCE_V1",
    "branch":branch,
    "head_sha":head,
    "runtime_authority":runtime,
    "run_rc":run_rc,
    "failed_step":failed_step,
    "status":payload.get("status"),
    "decision":payload.get("decision"),
    "active_match_evidence_pass":payload.get("active_match_evidence_pass"),
    "provider_label_record_count":payload.get("provider_label_record_count"),
    "csv_label_record_count":payload.get("csv_label_record_count"),
    "csv_surface_row_volume":coverage.get("csv_surface_row_volume"),
    "reviewed_semantic_surface_row_volume":coverage.get("reviewed_semantic_surface_row_volume"),
    "unknown_surface_row_volume":coverage.get("unknown_surface_row_volume"),
    "review_required_surface_row_volume":coverage.get("review_required_surface_row_volume"),
    "action_anchor_candidate_surface_row_volume":coverage.get("action_anchor_candidate_surface_row_volume"),
    "context_or_participation_surface_row_volume":coverage.get("context_or_participation_surface_row_volume"),
    "reference_or_derived_surface_row_volume":coverage.get("reference_or_derived_surface_row_volume"),
    "administrative_or_meta_surface_row_volume":coverage.get("administrative_or_meta_surface_row_volume"),
    "xml_example_support_label_count":coverage.get("xml_example_support_label_count"),
    "xlsx_aggregate_label_count":coverage.get("xlsx_aggregate_label_count"),
    "cross_format_conflict_count":(payload.get("cross_format_consistency") or {}).get("conflict_count"),
    "hard_block_hits":payload.get("hard_block_hits"),
    "review_hits":payload.get("review_hits"),
    "canonical_event_count":"UNKNOWN",
    "production_release":False,
    "phone_handoff_mode":"ONE_ZIP_ONLY",
    "phone_runtime_pytest":False,
    "single_pass_upstream_refresh":True
}
(root/"HPFA_175_ACTIVE_MATCH_EVIDENCE_MANIFEST.json").write_text(
    json.dumps(record, ensure_ascii=False, indent=2)+"\n", encoding="utf-8"
)

lines=[
    "HPFA #175 ACTIVE_MATCH RESULT",
    f"branch={branch}",
    f"head_sha={head}",
    f"run_rc={run_rc}",
    f"failed_step={failed_step or ''}",
    f"status={record['status']}",
    f"decision={record['decision']}",
    f"active_match_evidence_pass={record['active_match_evidence_pass']}",
    f"provider_label_record_count={record['provider_label_record_count']}",
    f"hard_block_hits={record['hard_block_hits']}",
    f"review_hits={record['review_hits']}",
    f"canonical_event_count=UNKNOWN",
    f"production_release=false",
]
(root/"provider_label_value_semantics_result_v1.txt").write_text(
    "\n".join(lines)+"\n", encoding="utf-8"
)
PY

python - "$TMP_ROOT" "$ZIP" <<'PY'
import hashlib, json, sys, zipfile
from pathlib import Path

root=Path(sys.argv[1])
zip_path=Path(sys.argv[2])

files=[p for p in root.iterdir() if p.is_file()]
hashes={}
for p in sorted(files):
    h=hashlib.sha256(p.read_bytes()).hexdigest()
    hashes[p.name]={"sha256":h,"size":p.stat().st_size}

(root/"HPFA_175_ZIP_CONTENT_MANIFEST.json").write_text(
    json.dumps({"files":hashes}, ensure_ascii=False, indent=2)+"\n",
    encoding="utf-8"
)

files=[p for p in root.iterdir() if p.is_file()]
with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED) as z:
    for p in sorted(files):
        z.write(p,arcname=p.name)
PY

echo
echo "=============================="
echo "HPFA #175 KISA SONUÇ"
echo "=============================="
grep -E '^(run_rc|failed_step|status|decision|active_match_evidence_pass|provider_label_record_count|hard_block_hits|review_hits|canonical_event_count|production_release)=' "$RESULT" || true
echo "ZIP=$ZIP"
echo "=============================="

exit "$FINAL_RC"
