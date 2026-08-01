#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO_URL="https://github.com/Hikmetpinarbas/hpfa.git"
BRANCH="agent/match-context-slicer-lite-v1"
REPO="${HPFA_REPO:-$HOME/hp/repos/hpfa}"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"

fail() {
  mkdir -p "$OUT" 2>/dev/null || true
  printf 'FAIL: %s\n' "$1" | tee "$OUT/match_context_slicer_bootstrap_v1.txt" >&2
  exit 2
}

case "$OUT" in
  /sdcard/Download/HPFA|/storage/emulated/0/Download/HPFA) ;;
  */HPFA/*) fail "nested_phone_output_directory_rejected" ;;
  *) fail "phone_output_directory_not_allowed:$OUT" ;;
esac
[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"
if [[ -e "$REPO" && ! -d "$REPO/.git" ]]; then
  fail "product_repo_path_exists_but_is_not_git:$REPO"
fi
if [[ ! -d "$REPO/.git" ]]; then
  mkdir -p "$(dirname "$REPO")"
  git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$REPO"
fi
[[ -z "$(git -C "$REPO" status --porcelain)" ]] || fail "product_repo_worktree_not_clean:$REPO"

git -C "$REPO" fetch origin "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"
REMOTE_HEAD="$(git -C "$REPO" rev-parse "refs/remotes/origin/$BRANCH" 2>/dev/null || true)"
[[ "$REMOTE_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "remote_head_missing_or_invalid:$REMOTE_HEAD"
REQUESTED_EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
if [[ -n "$REQUESTED_EXPECTED_HEAD" ]]; then
  [[ "$REQUESTED_EXPECTED_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "requested_expected_head_invalid"
  [[ "$REQUESTED_EXPECTED_HEAD" == "$REMOTE_HEAD" ]] || fail "remote_head_mismatch:$REMOTE_HEAD expected:$REQUESTED_EXPECTED_HEAD"
fi
if git -C "$REPO" show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git -C "$REPO" switch "$BRANCH"
else
  git -C "$REPO" switch --track "origin/$BRANCH"
fi
git -C "$REPO" merge --ff-only "origin/$BRANCH" || fail "product_repo_non_fast_forward:$REPO"
ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"
[[ "$ACTUAL_HEAD" == "$REMOTE_HEAD" ]] || fail "product_repo_head_not_remote_head"

if ! python - <<'PY'
import openpyxl
import pytest
print(f"pytest_version={pytest.__version__}")
print(f"openpyxl_version={openpyxl.__version__}")
PY
then
  python -m pip install --upgrade pytest openpyxl || fail "python_dependencies_install_failed"
fi

export HPFA_REPO="$REPO"
export HPFA_ACTIVE_MATCH="$ACTIVE_MATCH"
export HPFA_EXPECTED_ACTIVE_MATCH="$ACTIVE_MATCH"
export HPFA_PHONE_OUTPUT="$OUT"
export HPFA_EXPECTED_HEAD="${REQUESTED_EXPECTED_HEAD:-$REMOTE_HEAD}"
export HPFA_EXPECTED_BRANCH="$BRANCH"
mkdir -p "$OUT"
{
  echo "product_repo=$REPO"
  echo "branch=$BRANCH"
  echo "head_sha=$ACTUAL_HEAD"
  echo "expected_head_sha=$HPFA_EXPECTED_HEAD"
  echo "runtime_authority=$ACTIVE_MATCH"
  echo "bootstrap_status=READY"
} | tee "$OUT/match_context_slicer_bootstrap_v1.txt"

set +e
bash "$REPO/tools/run_active_match_context_slicer_v1.sh"
RUN_RC="$?"
set -e

BUNDLE="$OUT/match_context_slicer_active_match_bundle_v1.zip"
BUNDLE_AUDIT="$OUT/match_context_slicer_bundle_v1.txt"
rm -f "$BUNDLE" "$BUNDLE_AUDIT"
python - "$OUT" "$BUNDLE" "$ACTUAL_HEAD" "$RUN_RC" <<'PY' | tee "$BUNDLE_AUDIT"
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

out = Path(sys.argv[1]).expanduser().resolve(strict=False)
bundle = Path(sys.argv[2]).expanduser().resolve(strict=False)
head = sys.argv[3]
run_rc = int(sys.argv[4])
allowed = {
    Path("/sdcard/Download/HPFA").resolve(strict=False),
    Path("/storage/emulated/0/Download/HPFA").resolve(strict=False),
}
if out not in allowed or bundle.parent != out:
    raise SystemExit("bundle_output_directory_invalid")
prefixes = (
    "match_context_slicer_",
    "phase_aware_sequence_refinement_",
    "event_derived_phase_state_",
    "visible_action_sequence_candidate_admission_",
    "selected_event_consequence_surface_",
    "selected_action_consequence_surface_",
)
excluded = {bundle.name, "match_context_slicer_bundle_v1.txt"}
files = sorted(
    path
    for path in out.iterdir()
    if path.is_file()
    and path.name not in excluded
    and path.suffix.casefold() != ".zip"
    and path.name.startswith(prefixes)
)
if not files:
    raise SystemExit("bundle_source_outputs_missing")
entries = [
    {
        "name": path.name,
        "size_bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    for path in files
]
manifest = {
    "bundle_version": "match_context_slicer_active_match_bundle_v1",
    "runtime_code_head_sha": head,
    "run_rc": run_rc,
    "output_directory": str(out),
    "file_count": len(entries),
    "files": entries,
    "canonical_event_count": "UNKNOWN",
    "production_release": False,
}
with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
    for path in files:
        archive.write(path, arcname=path.name)
    archive.writestr(
        "HPFA_BUNDLE_MANIFEST.json",
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
print("HPFA MATCH CONTEXT SLICER PHONE OUTPUT BUNDLE")
print(f"bundle_path={bundle}")
print(f"bundle_file_count={len(entries)}")
print(f"bundle_sha256={hashlib.sha256(bundle.read_bytes()).hexdigest()}")
print(f"runtime_code_head_sha={head}")
print(f"run_rc={run_rc}")
print("canonical_event_count=UNKNOWN")
print("production_release=false")
PY

exit "$RUN_RC"
