#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

BRANCH="work/reconstruct-185-research-hardened-v1"
DEFAULT_ORIGIN_URL="https://github.com/Hikmetpinarbas/hpfa.git"
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
    *) return 1 ;;
  esac
}

[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"
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

ORIGIN_URL="${HPFA_TRUSTED_ORIGIN:-$DEFAULT_ORIGIN_URL}"
origin_is_trusted "$ORIGIN_URL" || fail "product_repo_origin_transport_or_identity_rejected:$ORIGIN_URL"

clean_git(){
  env -i \
    -u GIT_SSL_NO_VERIFY \
    HOME="${HOME:-}" \
    PATH="${PATH:-/data/data/com.termux/files/usr/bin:/system/bin}" \
    TMPDIR="${TMPDIR:-${PREFIX:-/data/data/com.termux/files/usr}/tmp}" \
    LC_ALL=C \
    GIT_CONFIG_GLOBAL=/dev/null \
    GIT_CONFIG_SYSTEM=/dev/null \
    GIT_CONFIG_NOSYSTEM=1 \
    GIT_SSH_COMMAND="ssh" \
    git -c core.fsmonitor=false -c core.hooksPath=/dev/null \
        -c core.untrackedCache=false -c core.sshCommand=ssh \
        -c http.sslVerify=true -c protocol.ext.allow=never "$@"
}

FETCH_TMP="$(mktemp -d "${TMPDIR:-/tmp}/hpfa-185-reflection-fetch.XXXXXX")" \
  || fail "trusted_fetch_tempdir_create_failed"
cleanup(){ rm -rf "$FETCH_TMP"; }
trap cleanup EXIT INT TERM HUP
FETCH_REPO="$FETCH_TMP/fetch.git"
WORK_REPO="$FETCH_TMP/work"

clean_git init --bare "$FETCH_REPO" >/dev/null
clean_git --git-dir="$FETCH_REPO" remote add origin "$ORIGIN_URL"
clean_git --git-dir="$FETCH_REPO" fetch --no-tags --no-recurse-submodules \
  "$ORIGIN_URL" "$BRANCH:refs/heads/remote"
REMOTE_HEAD="$(clean_git --git-dir="$FETCH_REPO" rev-parse refs/heads/remote 2>/dev/null || true)"
[[ "$REMOTE_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "remote_head_missing_or_invalid:$REMOTE_HEAD"

EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
[[ -n "$EXPECTED_HEAD" ]] || fail "expected_head_required:set_HPFA_EXPECTED_HEAD"
[[ "$EXPECTED_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "requested_expected_head_invalid:$EXPECTED_HEAD"
[[ "$REMOTE_HEAD" == "$EXPECTED_HEAD" ]] || fail "remote_head_mismatch:$REMOTE_HEAD expected:$EXPECTED_HEAD"

clean_git --git-dir="$FETCH_REPO" worktree add -B "$BRANCH" "$WORK_REPO" "$REMOTE_HEAD" >/dev/null
ACTUAL_HEAD="$(clean_git -C "$WORK_REPO" rev-parse HEAD)"
[[ "$ACTUAL_HEAD" == "$EXPECTED_HEAD" ]] || fail "trusted_worktree_head_mismatch:$ACTUAL_HEAD expected:$EXPECTED_HEAD"
[[ -z "$(clean_git -C "$WORK_REPO" status --porcelain --untracked-files=all)" ]] \
  || fail "trusted_worktree_not_clean:$WORK_REPO"

TRUSTED_PYTHON="/data/data/com.termux/files/usr/bin/python"
[[ -x "$TRUSTED_PYTHON" ]] || fail "trusted_python_interpreter_missing:$TRUSTED_PYTHON"
safe_python(){
  env -i \
    -u PYTHONPATH -u PYTHONHOME -u PYTHONSTARTUP -u PYTHONUSERBASE \
    -u PYTHONINSPECT -u PYTHONBREAKPOINT -u PYTHONPYCACHEPREFIX \
    HOME="${HOME:-}" \
    PATH="/data/data/com.termux/files/usr/bin:/system/bin" \
    TMPDIR="${TMPDIR:-/data/data/com.termux/files/usr/tmp}" \
    PYTHONNOUSERSITE=1 \
    "$TRUSTED_PYTHON" "$@"
}

ADAPTER="$WORK_REPO/triangulated_event_reflection_resolver_lite.py"
[[ -f "$ADAPTER" ]] || fail "reflection_runtime_adapter_missing:$ADAPTER"

TMP_ROOT="$FETCH_TMP/evidence"
mkdir -p "$TMP_ROOT"
REPORT="$TMP_ROOT/triangulated_event_reflection_resolver_lite_v1.json"
MANIFEST="$TMP_ROOT/HPFA_185_ACTIVE_MATCH_EVIDENCE_MANIFEST.json"
SUMMARY="$TMP_ROOT/HPFA_185_KISA_SONUC.txt"
ZIP="$OUT/HPFA_185_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.zip"
ZIP_TMP="$OUT/.HPFA_185_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.$$.zip.partial"
rm -f "$OUT"/HPFA_185_ACTIVE_MATCH_*.zip "$OUT"/.HPFA_185_ACTIVE_MATCH_*.zip.partial

RUN_RC=0
FAILED_STEP=""
if ! safe_python "$ADAPTER" --input-root "$ACTIVE_RESOLVED" --output "$REPORT"; then
  RUN_RC=$?
  [[ "$RUN_RC" -eq 0 ]] && RUN_RC=2
  FAILED_STEP="reflection_resolver"
fi

safe_python - "$REPORT" "$MANIFEST" "$SUMMARY" "$ACTUAL_HEAD" "$ACTIVE_RESOLVED" "$RUN_RC" "$FAILED_STEP" <<'PY'
import json, sys
from pathlib import Path

report_path, manifest_path, summary_path = map(Path, sys.argv[1:4])
head, runtime, run_rc_raw, failed = sys.argv[4:8]
run_rc = int(run_rc_raw)
try:
    report = json.loads(report_path.read_text(encoding="utf-8"))
except Exception:
    report = {}

bridge = report.get("content_source_role_bridge") or {}
execution_ok = (
    run_rc == 0
    and report.get("status") == "REVIEW_REQUIRED"
    and bridge.get("status") == "PASS"
    and int(bridge.get("unresolved_role_file_count") or 0) == 0
    and int(report.get("unique_surface_file_count") or 0) > 0
)
active_pass = bool(execution_ok)

manifest = {
    "bundle_version": "HPFA_185_ACTIVE_MATCH_EVIDENCE_V1",
    "head_sha": head,
    "runtime_authority": runtime,
    "run_rc": run_rc,
    "failed_step": failed or None,
    "status": report.get("status") if active_pass else "FAIL_CLOSED",
    "runtime_evidence_status": "ACTIVE_MATCH_EVIDENCE_PASS" if active_pass else "FAIL_CLOSED",
    "active_match_evidence_pass": active_pass,
    "decision": report.get("decision"),
    "surface_file_count": report.get("surface_file_count"),
    "unique_surface_file_count": report.get("unique_surface_file_count"),
    "surface_row_count": report.get("surface_row_count"),
    "reflection_group_count": report.get("reflection_group_count"),
    "single_surface_group_count": report.get("single_surface_group_count"),
    "multi_surface_group_count": report.get("multi_surface_group_count"),
    "serialization_role_audit_count": report.get("serialization_role_audit_count"),
    "serialization_exact_role_count": report.get("serialization_exact_role_count"),
    "serialization_discrepancy_role_count": report.get("serialization_discrepancy_role_count"),
    "serialization_pairing_review_role_count": report.get("serialization_pairing_review_role_count"),
    "duplicate_surface_file_reflection_count": report.get("duplicate_surface_file_reflection_count"),
    "content_source_role_bridge_status": bridge.get("status"),
    "resolved_role_counts": bridge.get("resolved_role_counts") or {},
    "filename_support_used_for_role_admission": False,
    "physical_action_identity_truth": False,
    "same_upstream_origin_truth": False,
    "independent_source_vote_allowed": False,
    "action_count_claim_allowed": False,
    "true_action_count": "UNKNOWN",
    "canonical_event_count": "UNKNOWN",
    "production_release": False,
}
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

fields = [
    ("run_rc", run_rc),
    ("failed_step", failed),
    ("status", manifest["status"]),
    ("active_match_evidence_pass", active_pass),
    ("decision", manifest["decision"]),
    ("surface_file_count", manifest["surface_file_count"]),
    ("unique_surface_file_count", manifest["unique_surface_file_count"]),
    ("surface_row_count", manifest["surface_row_count"]),
    ("reflection_group_count", manifest["reflection_group_count"]),
    ("single_surface_group_count", manifest["single_surface_group_count"]),
    ("multi_surface_group_count", manifest["multi_surface_group_count"]),
    ("serialization_role_audit_count", manifest["serialization_role_audit_count"]),
    ("serialization_exact_role_count", manifest["serialization_exact_role_count"]),
    ("serialization_discrepancy_role_count", manifest["serialization_discrepancy_role_count"]),
    ("serialization_pairing_review_role_count", manifest["serialization_pairing_review_role_count"]),
    ("content_source_role_bridge_status", manifest["content_source_role_bridge_status"]),
    ("resolved_role_counts", json.dumps(manifest["resolved_role_counts"], ensure_ascii=False, separators=(",", ":"))),
    ("filename_support_used_for_role_admission", "false"),
    ("physical_action_identity_truth", "false"),
    ("independent_source_vote_allowed", "false"),
    ("canonical_event_count", "UNKNOWN"),
    ("production_release", "false"),
]
text = ["==============================", "HPFA #185 KISA SONUÇ", "=============================="]
text += [f"{key}={value}" for key, value in fields]
text += ["=============================="]
summary_path.write_text("\n".join(text) + "\n", encoding="utf-8")
print(summary_path.read_text(encoding="utf-8"), end="")
PY

safe_python - "$TMP_ROOT" "$ZIP_TMP" <<'PY'
import sys, zipfile
from pathlib import Path
root=Path(sys.argv[1]); out=Path(sys.argv[2])
with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for path in sorted(root.iterdir()):
        if path.is_file():
            z.write(path, arcname=path.name)
PY
mv "$ZIP_TMP" "$ZIP"
printf 'ZIP=%s\n' "$ZIP"

if [[ "$RUN_RC" -ne 0 ]]; then
  exit "$RUN_RC"
fi
