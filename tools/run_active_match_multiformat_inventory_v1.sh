#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

OUT="/sdcard/Download/HPFA"
EXPECTED_BRANCH="multiformat-file-inventory-lite-v1"
EXPECTED_REPO_SLUG="hikmetpinarbas/hpfa"
DEFAULT_ACTIVE="$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current"

fail() {
  local message="$1"
  if [[ -d "$OUT" ]] || mkdir -p "$OUT" 2>/dev/null; then
    printf 'FAIL: %s\n' "$message" | tee "$OUT/multiformat_file_inventory_active_match_v1.txt" >&2
  else
    printf 'FAIL: %s\n' "$message" >&2
  fi
  exit 1
}

normalize_remote_slug() {
  local remote="${1:-}"
  remote="${remote%/}"
  remote="${remote%.git}"
  remote="${remote#https://github.com/}"
  remote="${remote#http://github.com/}"
  remote="${remote#git@github.com:}"
  remote="${remote#ssh://git@github.com/}"
  printf '%s\n' "${remote,,}"
}

repo_matches_hpfa() {
  local candidate="$1"
  [[ -d "$candidate/.git" ]] || return 1
  local remote slug
  remote="$(git -C "$candidate" remote get-url origin 2>/dev/null || true)"
  slug="$(normalize_remote_slug "$remote")"
  [[ "$slug" == "$EXPECTED_REPO_SLUG" ]]
}

self_test_repo_guard() {
  local tmp repo
  tmp="$(mktemp -d)"
  repo="$tmp/repo"
  git init -q "$repo"
  git -C "$repo" remote add origin "https://github.com/Hikmetpinarbas/hpfa.git"
  repo_matches_hpfa "$repo" || fail "self_test_exact_origin_rejected"
  git -C "$repo" remote set-url origin "https://github.com/Hikmetpinarbas/hpfa-main.git"
  if repo_matches_hpfa "$repo"; then
    fail "self_test_prefix_collision_accepted"
  fi
  git -C "$repo" remote set-url origin "git@github.com:Hikmetpinarbas/hpfa.git"
  repo_matches_hpfa "$repo" || fail "self_test_ssh_origin_rejected"
  rm -rf "$tmp"
  echo "repo_origin_guard_self_test=PASS"
}

if [[ "${1:-}" == "--self-test-repo-guard" ]]; then
  self_test_repo_guard
  exit 0
fi

mkdir -p "$OUT"

resolve_repo() {
  local candidate

  if [[ -n "${HPFA_REPO:-}" ]]; then
    repo_matches_hpfa "$HPFA_REPO" || fail "hpfa_repo_not_found_or_wrong_remote:$HPFA_REPO"
    printf '%s\n' "$HPFA_REPO"
    return 0
  fi

  for candidate in \
    "$PWD" \
    "$HOME/hp/repos/hpfa" \
    "$HOME/hpfa"
  do
    if repo_matches_hpfa "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  while IFS= read -r git_dir; do
    candidate="${git_dir%/.git}"
    if repo_matches_hpfa "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done < <(find "$HOME" -maxdepth 6 -type d -name .git 2>/dev/null | sort)

  fail "hpfa_product_repo_not_found:set_HPFA_REPO_to_the_git_checkout"
}

REPO="$(resolve_repo)"
ACTIVE="${HPFA_ACTIVE_MATCH:-$DEFAULT_ACTIVE}"

[[ -d "$ACTIVE" ]] || fail "active_match_runtime_not_found:$ACTIVE"

ACTUAL_ROOT="$(git -C "$REPO" rev-parse --show-toplevel)"
ACTUAL_BRANCH="$(git -C "$REPO" branch --show-current)"
ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"
ORIGIN_URL="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"

[[ "$ACTUAL_ROOT" == "$REPO" ]] || REPO="$ACTUAL_ROOT"
[[ "$ACTUAL_BRANCH" == "$EXPECTED_BRANCH" ]] || fail "unexpected_branch:$ACTUAL_BRANCH expected:$EXPECTED_BRANCH repo:$REPO"
[[ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]] || fail "tracked_worktree_not_clean:$REPO"

cd "$REPO"

python -m py_compile \
  hpfa/modules/core/multiformat_file_inventory_lite/src/multiformat_file_inventory.py \
  hpfa/modules/core/multiformat_file_inventory_lite/src/multiformat_file_inventory_impl.py \
  hpfa/modules/core/multiformat_file_inventory_lite/tests/test_multiformat_file_inventory.py \
  hpfa/modules/core/multiformat_file_inventory_lite/tests/test_review_regressions.py \
  multiformat_file_inventory.py

python -m pytest -q \
  hpfa/modules/core/multiformat_file_inventory_lite/tests \
  | tee "$OUT/multiformat_file_inventory_pytest_v1.txt"

set +e
python multiformat_file_inventory.py \
  --input-root "$ACTIVE" \
  --runtime-authority "$ACTIVE" \
  --active-match-execution \
  --out "$OUT" \
  | tee "$OUT/multiformat_file_inventory_active_match_v1.txt"
RUN_RC="${PIPESTATUS[0]}"
set -e

python - "$OUT/multiformat_file_inventory_lite_v1.json" <<'PY' \
  | tee "$OUT/multiformat_file_inventory_analyst_audit_v1.txt"
from pathlib import Path
import json
import sys

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
duplicates = payload.get("duplicate_report") or {}
print("HPFA MULTIFORMAT FILE INVENTORY ACTIVE_MATCH AUDIT")
print(f"status={payload.get('status')}")
print(f"total_file_path_count={payload.get('total_file_path_count')}")
print(f"supported_file_count={payload.get('supported_file_count')}")
print(f"unique_supported_content_file_count={payload.get('unique_content_file_count')}")
print(f"unsupported_file_count={payload.get('unsupported_file_count')}")
print(f"unresolved_unsupported_file_count={payload.get('unresolved_unsupported_file_count')}")
print(f"reference_only_unsupported_file_count={payload.get('reference_only_unsupported_file_count')}")
print(f"exact_duplicate_group_count={duplicates.get('exact_duplicate_group_count')}")
print(f"exact_duplicate_reflection_count={duplicates.get('exact_duplicate_reflection_count')}")
print(f"duplicate_file_conflict_count={duplicates.get('duplicate_file_conflict_count')}")
print(f"hard_block_hits={payload.get('hard_block_hits')}")
print(f"active_match_evidence_pass={payload.get('active_match_evidence_pass')}")
print(f"canonical_event_count={payload.get('canonical_event_count')}")
print(f"production_release={payload.get('production_release')}")
PY

{
  echo "product_repo=$REPO"
  echo "origin_url=$ORIGIN_URL"
  echo "branch=$ACTUAL_BRANCH"
  echo "head_sha=$ACTUAL_HEAD"
  echo "runtime_authority=$ACTIVE"
  echo "run_rc=$RUN_RC"
  echo "main_output=$OUT/multiformat_file_inventory_lite_v1.json"
  echo "inventory_json=$OUT/input_file_inventory.json"
  echo "inventory_tsv=$OUT/input_file_inventory.tsv"
  echo "unsupported_report=$OUT/unsupported_file_report.json"
  echo "duplicate_report=$OUT/duplicate_file_fingerprint_report.json"
  echo "decision_txt=$OUT/multiformat_ingest_decision_v1.txt"
  echo "analyst_audit=$OUT/multiformat_file_inventory_analyst_audit_v1.txt"
  echo "canonical_event_count=UNKNOWN"
  echo "production_release=false"
} | tee "$OUT/multiformat_file_inventory_result_v1.txt"

exit "$RUN_RC"
