#!/data/data/com.termux/files/usr/bin/bash
set -u -o pipefail

EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
EXPECTED_BRANCH="${HPFA_EXPECTED_BRANCH:-}"
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
[[ -d "$REPO" ]] || fail "product_repo_missing:$REPO"
git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "product_repo_not_git_checkout:$REPO"
[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"

ORIGIN_URL="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"
ORIGIN_SLUG="$(normalize_origin "$ORIGIN_URL")"
ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD 2>/dev/null || true)"
ACTUAL_BRANCH="$(git -C "$REPO" branch --show-current 2>/dev/null || true)"
[[ "$ORIGIN_SLUG" == "$EXPECTED_REPO_SLUG" ]] || fail "product_repo_origin_mismatch:$ORIGIN_URL"
[[ "$ACTUAL_HEAD" == "$EXPECTED_HEAD" ]] || fail "execution_head_mismatch:actual=$ACTUAL_HEAD expected=$EXPECTED_HEAD"
if [[ -n "$EXPECTED_BRANCH" ]]; then
  [[ "$ACTUAL_BRANCH" == "$EXPECTED_BRANCH" ]] || fail "execution_branch_mismatch:actual=$ACTUAL_BRANCH expected=$EXPECTED_BRANCH"
fi
[[ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]] || fail "tracked_worktree_not_clean:$REPO"

for required in \
  active_match_full_run.py \
  episode_feature_vector.py \
  hpfa/modules/core/episode_feature_vector_lite/src/episode_feature_vector.py; do
  [[ -f "$REPO/$required" ]] || fail "required_product_file_missing:$required"
done

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

SURFACE_COUNT="$(find "$ACTIVE_RESOLVED" -maxdepth 1 -type f \( -iname '*.csv' -o -iname '*.xml' -o -iname '*.xlsx' \) | wc -l | tr -d ' ')"
[[ "${SURFACE_COUNT:-0}" -gt 0 ]] || fail "active_match_surface_files_missing"

TMP_ROOT="${TMPDIR:-${PREFIX:-/data/data/com.termux/files/usr}/tmp}/hpfa_episode_feature_${ACTUAL_HEAD:0:12}_$$"
mkdir -p "$TMP_ROOT"
LOG="$TMP_ROOT/episode_feature_active_match_runner.log"
RESULT="$TMP_ROOT/episode_feature_active_match_result_v1.txt"
MANIFEST="$TMP_ROOT/episode_feature_active_match_manifest_v1.json"
ZIP="$OUT/HPFA_EPISODE_FEATURE_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.zip"
ZIP_TMP="$OUT/.HPFA_EPISODE_FEATURE_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.$$.zip.partial"
rm -f "$ZIP" "$ZIP_TMP"
trap 'rm -rf "$TMP_ROOT"; rm -f "$ZIP_TMP"' EXIT
trap 'exit 130' INT TERM HUP

cd "$REPO"
set +e
python active_match_full_run.py \
  --match-dir "$ACTIVE_RESOLVED" \
  --out-dir "$TMP_ROOT" \
  >"$LOG" 2>&1
RUN_RC=$?
set -e

python - "$TMP_ROOT" "$ACTUAL_BRANCH" "$ACTUAL_HEAD" "$ACTIVE_RESOLVED" "$SURFACE_COUNT" "$RUN_RC" <<'PY'
import json, sys
from pathlib import Path

root=Path(sys.argv[1])
branch=sys.argv[2]
head=sys.argv[3]
runtime=sys.argv[4]
surface_count=int(sys.argv[5])
run_rc=int(sys.argv[6])

def load(name):
    p=root/name
    if not p.exists():
        return {}
    try:
        data=json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data,dict) else {}

full=load("active_match_full_run_lite_v1.json")
feature=load("episode_feature_vector_lite_v1.json")
engineering=full.get("engineering_evidence") or {}
record={
    "bundle_version":"HPFA_EPISODE_FEATURE_ACTIVE_MATCH_V1",
    "branch":branch or "DETACHED_HEAD",
    "head_sha":head,
    "runtime_authority":runtime,
    "surface_file_count":surface_count,
    "run_rc":run_rc,
    "full_run_output_present":bool(full),
    "feature_output_present":bool(feature),
    "full_run_valid":engineering.get("valid_run"),
    "feature_status":feature.get("status"),
    "episode_feature_vector_count":feature.get("episode_feature_vector_count"),
    "total_eligible_action_candidate_count":feature.get("total_eligible_action_candidate_count"),
    "total_support_only_context_count":feature.get("total_support_only_context_count"),
    "total_unresolved_semantics_context_count":feature.get("total_unresolved_semantics_context_count"),
    "eligible_action_family_candidate_counts":feature.get("eligible_action_family_candidate_counts"),
    "point_episode_count":feature.get("point_episode_count"),
    "density_not_applicable_zero_duration_count":feature.get("density_not_applicable_zero_duration_count"),
    "feature_assignment_complete":feature.get("feature_assignment_complete"),
    "hard_block_hits":feature.get("hard_block_hits"),
    "review_hits":feature.get("review_hits"),
    "canonical_event_count":feature.get("canonical_event_count","UNKNOWN"),
    "production_release":feature.get("production_release",False),
}
(root/"episode_feature_active_match_manifest_v1.json").write_text(
    json.dumps(record,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8"
)
lines=[
    "=== HPFA EPISODE FEATURE ACTIVE_MATCH CHECK ===",
    f"branch = {record['branch']}",
    f"head = {record['head_sha']}",
    f"surface_files = {record['surface_file_count']}",
    f"run_rc = {record['run_rc']}",
    f"full_run_output_present = {record['full_run_output_present']}",
    f"feature_output_present = {record['feature_output_present']}",
    f"full_run_valid = {record['full_run_valid']}",
    f"status = {record['feature_status']}",
    f"episode_cards = {record['episode_feature_vector_count']}",
    f"clean_action_candidates = {record['total_eligible_action_candidate_count']}",
    f"support_context = {record['total_support_only_context_count']}",
    f"unresolved = {record['total_unresolved_semantics_context_count']}",
    f"action_families = {record['eligible_action_family_candidate_counts']}",
    f"point_episodes = {record['point_episode_count']}",
    f"density_NA_zero_duration = {record['density_not_applicable_zero_duration_count']}",
    f"assignment_complete = {record['feature_assignment_complete']}",
    f"hard_blocks = {record['hard_block_hits']}",
    f"review_hits = {record['review_hits']}",
    f"canonical_event_count = {record['canonical_event_count']}",
    f"production_release = {record['production_release']}",
]
(root/"episode_feature_active_match_result_v1.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
print("\n".join(lines))
PY
POST_RC=$?

if [[ "$RUN_RC" -ne 0 || ! -f "$TMP_ROOT/episode_feature_vector_lite_v1.json" ]]; then
  echo
  echo "=== RUNNER ERROR TAIL ==="
  tail -n 80 "$LOG" || true
fi

python - "$TMP_ROOT" "$ZIP_TMP" <<'PY'
import sys, zipfile
from pathlib import Path
root=Path(sys.argv[1]); out=Path(sys.argv[2])
keep={
    "active_match_full_run_lite_v1.json",
    "episode_feature_vector_lite_v1.json",
    "analyst_episode_locator_lite_v1.json",
    "context_action_semantics_rebind_lite_v1.json",
    "episode_feature_active_match_runner.log",
    "episode_feature_active_match_result_v1.txt",
    "episode_feature_active_match_manifest_v1.json",
}
with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED) as z:
    for p in sorted(root.iterdir()):
        if p.is_file() and p.name in keep:
            z.write(p,arcname=p.name)
PY
PACK_RC=$?
if [[ "$PACK_RC" -eq 0 ]]; then
  mv -f "$ZIP_TMP" "$ZIP"
  echo "ZIP=$ZIP"
else
  rm -f "$ZIP_TMP"
  echo "ZIP=NOT_CREATED"
fi

echo "HPFA_EPISODE_FEATURE_ACTIVE_MATCH_RC=$RUN_RC"

if [[ "$RUN_RC" -ne 0 ]]; then exit "$RUN_RC"; fi
if [[ "$POST_RC" -ne 0 ]]; then exit "$POST_RC"; fi
[[ -f "$TMP_ROOT/episode_feature_vector_lite_v1.json" ]] || exit 2
exit 0
