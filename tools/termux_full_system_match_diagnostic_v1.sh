#!/data/data/com.termux/files/usr/bin/bash
set -uo pipefail

BRANCH="feature/zfgv-action-grammar-synced-v1"
REMOTE="https://github.com/Hikmetpinarbas/hpfa.git"
SHA="${1:-}"
RUNTIME_ROOT="$HOME/hpfa_claim_integrity/hpfa"
RUNTIME="$RUNTIME_ROOT/runtime/active_single_match/current"
DEST="/sdcard/Download/HPFA"
TMP_BASE="${TMPDIR:-${PREFIX:-/data/data/com.termux/files/usr}/tmp}"
DISCOVERY_LOG=""

mkdir -p "$DEST"

find_product_repo() {
  local gitdir root url
  for root in \
    "$HOME/hpfa" \
    "$HOME/HPFA" \
    "$HOME/hpfa_repo" \
    "$HOME/projects/hpfa" \
    "$HOME/repos/hpfa"
  do
    if git -C "$root" rev-parse --git-dir >/dev/null 2>&1; then
      url="$(git -C "$root" remote get-url origin 2>/dev/null || true)"
      case "$url" in
        *Hikmetpinarbas/hpfa*|*hikmetpinarbas/hpfa*) printf '%s\n' "$root"; return 0 ;;
      esac
    fi
  done

  while IFS= read -r gitdir; do
    root="${gitdir%/.git}"
    url="$(git -C "$root" remote get-url origin 2>/dev/null || true)"
    case "$url" in
      *Hikmetpinarbas/hpfa*|*hikmetpinarbas/hpfa*) printf '%s\n' "$root"; return 0 ;;
    esac
  done < <(find "$HOME" -maxdepth 6 -type d -name .git 2>/dev/null)
  return 1
}

SOURCE_REPO="$(find_product_repo || true)"

if [ -z "$SHA" ]; then
  if [ -n "$SOURCE_REPO" ]; then
    git -C "$SOURCE_REPO" fetch -q origin "$BRANCH" || true
    SHA="$(git -C "$SOURCE_REPO" rev-parse FETCH_HEAD 2>/dev/null || true)"
  fi
  if [ -z "$SHA" ]; then
    SHA="$(git ls-remote "$REMOTE" "refs/heads/$BRANCH" 2>/dev/null | awk 'NR==1{print $1}')"
  fi
fi

if [ -z "$SHA" ]; then
  echo "FAIL: current development head could not be resolved"
  exit 2
fi

SHORT="${SHA:0:7}"
STAMP="$(date +%Y%m%d_%H%M%S)"
WORK="$(mktemp -d "$TMP_BASE/hpfa_full_diag_${SHORT}_XXXXXX")"
PRODUCT="$WORK/product"
OUT="$WORK/out"
PKG="$DEST/HPFA_FULL_DIAGNOSTIC_${SHORT}_${STAMP}.tar.gz"
RUN_LOG="$OUT/HPFA_PHYSICAL_RUN.log"
EXACT_RC=98
DIAG_RC=98

cleanup() {
  command -v termux-wake-unlock >/dev/null 2>&1 && termux-wake-unlock >/dev/null 2>&1 || true
  rm -rf "$WORK" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

mkdir -p "$OUT"
: > "$RUN_LOG"

log() {
  printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*" | tee -a "$RUN_LOG"
}

log "HPFA FULL SYSTEM MATCH DIAGNOSTIC PHYSICAL ACCEPTANCE"
log "EXPECTED_HEAD=$SHA"
log "RUNTIME_AUTHORITY=$RUNTIME"
log "SOURCE_REPO=${SOURCE_REPO:-REMOTE_CLONE}"

if [ ! -d "$RUNTIME" ]; then
  log "FAIL=CANONICAL_ACTIVE_MATCH_MISSING:$RUNTIME"
  exit 2
fi

log "CHECKPOINT=EXACT_CHECKOUT"
if [ -n "$SOURCE_REPO" ]; then
  git -C "$SOURCE_REPO" fetch -q origin "$BRANCH" >>"$RUN_LOG" 2>&1 || true
  if git -C "$SOURCE_REPO" cat-file -e "$SHA^{commit}" 2>/dev/null; then
    if ! git clone --quiet --shared --no-checkout "$SOURCE_REPO" "$PRODUCT" >>"$RUN_LOG" 2>&1; then
      log "FAIL=LOCAL_TEMP_EXACT_CLONE_FAILED"
      exit 2
    fi
  else
    SOURCE_REPO=""
  fi
fi

if [ -z "$SOURCE_REPO" ]; then
  if ! git clone --quiet --no-checkout "$REMOTE" "$PRODUCT" >>"$RUN_LOG" 2>&1; then
    log "FAIL=REMOTE_TEMP_EXACT_CLONE_FAILED"
    exit 2
  fi
fi

if ! git -C "$PRODUCT" checkout --quiet --detach "$SHA" >>"$RUN_LOG" 2>&1; then
  log "FAIL=EXACT_HEAD_CHECKOUT_FAILED"
  exit 2
fi
ACTUAL_SHA="$(git -C "$PRODUCT" rev-parse HEAD 2>/dev/null || true)"
if [ "$ACTUAL_SHA" != "$SHA" ]; then
  log "FAIL_CLOSED=EXACT_HEAD_MISMATCH observed=$ACTUAL_SHA"
  exit 3
fi

command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock >/dev/null 2>&1 || true

log "CHECKPOINT=EXACT_HEAD_ACTIVE_MATCH"
START_EXACT="$(date +%s)"
python -u "$PRODUCT/active_match_exact_head_run_v1.py" \
  --match-dir "$RUNTIME" \
  --out-dir "$OUT" \
  --expected-product-commit "$SHA" \
  >>"$RUN_LOG" 2>&1
EXACT_RC=$?
END_EXACT="$(date +%s)"
EXACT_SECONDS=$((END_EXACT-START_EXACT))
log "EXACT_HEAD_RUN_RC=$EXACT_RC elapsed_seconds=$EXACT_SECONDS"

log "CHECKPOINT=ENGINEERING_AND_DIAGNOSTIC"
START_DIAG="$(date +%s)"
HPFA_PRODUCT="$PRODUCT" HPFA_OUT="$OUT" HPFA_SHA="$SHA" python -u - <<'PY' >>"$RUN_LOG" 2>&1
import json
import os
import sys
from pathlib import Path

product = Path(os.environ["HPFA_PRODUCT"]).resolve()
out = Path(os.environ["HPFA_OUT"]).resolve()
sha = os.environ["HPFA_SHA"]

src = product / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
sys.path.insert(0, str(product))
sys.path.insert(0, str(src))
os.chdir(product)

import full_system_match_diagnostic as diagnostic
import full_system_match_diagnostic_harness as harness

engineering = harness.run_engineering_checks(product, out)
full_spine_path = out / "active_match_full_spine_v1.json"

summary = {
    "head": sha,
    "engineering_status": engineering.get("status"),
    "diagnostic_status": "NOT_RUN_NO_FULL_SPINE",
    "canonical_event_count": "UNKNOWN",
    "true_action_count": "UNKNOWN",
    "production_release": False,
}

if full_spine_path.is_file():
    result = diagnostic.build_diagnostic(
        out,
        repository="Hikmetpinarbas/hpfa",
        branch="feature/zfgv-action-grammar-synced-v1",
        pr="359",
        head=sha,
    )
    result = harness.apply_engineering_states(result, engineering)
    diagnostic.write_outputs(out, result)
    harness.write_human_report(out, result)
    summary["diagnostic_status"] = result.get("status")
    summary["cross_artifact_consistency"] = result.get("cross_artifact_consistency", [])
    summary["gap_report"] = result.get("gap_report", [])
    summary["runtime_execution_state_counts"] = result.get("runtime_execution_state_counts", {})
    summary["engineering_test_state_counts"] = result.get("engineering_test_state_counts", {})
    summary["result_state_counts"] = result.get("result_state_counts", {})

exact_path = out / "active_match_exact_head_run_v1.json"
if exact_path.is_file():
    exact = json.loads(exact_path.read_text(encoding="utf-8"))
    summary["exact_head_acceptance_status"] = exact.get("status")
    summary["exact_product_commit_verified"] = exact.get("exact_product_commit_verified")
    summary["product_runtime_authority_separation_valid"] = exact.get("product_runtime_authority_separation_valid")
    summary["safe_finding_admission_decision_counts"] = exact.get("safe_finding_admission_decision_counts")
    summary["professional_finding_emitted_count"] = exact.get("professional_finding_emitted_count")
    summary["professional_emit_allowed"] = exact.get("professional_emit_allowed")

(out / "HPFA_OPERATOR_PHYSICAL_SUMMARY.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
DIAG_RC=$?
END_DIAG="$(date +%s)"
DIAG_SECONDS=$((END_DIAG-START_DIAG))
log "DIAGNOSTIC_RC=$DIAG_RC elapsed_seconds=$DIAG_SECONDS"

for name in HPFA_FAIL_LOCAL_PRODUCT_TEST_AUDIT.json HPFA_FULL_REPO_HEALTH_AUDIT.json; do
  if [ -f "$OUT/engineering_audit/$name" ]; then
    cp "$OUT/engineering_audit/$name" "$OUT/$name"
  fi
done

{
  echo "module_id=termux_full_system_match_diagnostic_v1"
  echo "expected_product_commit=$SHA"
  echo "observed_product_commit=$ACTUAL_SHA"
  echo "runtime_authority=$RUNTIME"
  echo "source_repo=${SOURCE_REPO:-REMOTE_CLONE}"
  echo "exact_head_run_return_code=$EXACT_RC"
  echo "exact_head_run_elapsed_seconds=$EXACT_SECONDS"
  echo "diagnostic_return_code=$DIAG_RC"
  echo "diagnostic_elapsed_seconds=$DIAG_SECONDS"
  echo "canonical_event_count=UNKNOWN"
  echo "true_action_count=UNKNOWN"
  echo "production_release=false"
  echo "merge_performed=false"
  echo "release_performed=false"
} > "$OUT/HPFA_PHYSICAL_ACCEPTANCE_MANIFEST.txt"

log "CHECKPOINT=PACKAGE"
rm -f "$PKG"
if tar -czf "$PKG" -C "$OUT" . >>"$RUN_LOG" 2>&1; then
  sync >/dev/null 2>&1 || true
  log "PACKAGE=$PKG"
else
  log "FAIL=PACKAGE_CREATION_FAILED"
  exit 2
fi

printf '\nHPFA_PACKAGE=%s\nEXACT_HEAD_RC=%s\nDIAGNOSTIC_RC=%s\n' "$PKG" "$EXACT_RC" "$DIAG_RC"
exit 0
