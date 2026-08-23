#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="${HPFA_REPO:-$HOME/hp/repos/hpfa}"
BRANCH="${HPFA_EXPECTED_BRANCH:-}"
EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"
EXPECTED_REPO_SLUG="hikmetpinarbas/hpfa"

fail(){ printf 'FAIL: %s\n' "$1" >&2; exit 2; }
normalize_origin(){
  local value="${1:-}"
  value="${value%/}"; value="${value%.git}"
  value="${value#https://github.com/}"; value="${value#http://github.com/}"
  value="${value#git@github.com:}"; value="${value#ssh://git@github.com/}"
  printf '%s\n' "${value,,}"
}

[[ -n "$BRANCH" ]] || fail "expected_branch_required:set_HPFA_EXPECTED_BRANCH"
[[ "$EXPECTED_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "expected_head_required_or_invalid:set_HPFA_EXPECTED_HEAD"
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

[[ -d "$REPO" ]] || fail "product_repo_missing:$REPO"
git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "product_repo_not_git_checkout:$REPO"
[[ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]] || fail "product_repo_worktree_not_clean:$REPO"

ORIGIN_URL="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"
ORIGIN_SLUG="$(normalize_origin "$ORIGIN_URL")"
[[ "$ORIGIN_SLUG" == "$EXPECTED_REPO_SLUG" ]] || fail "product_repo_origin_mismatch:$ORIGIN_URL"

git -C "$REPO" fetch origin "$BRANCH"
if git -C "$REPO" show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git -C "$REPO" switch "$BRANCH"
else
  git -C "$REPO" switch -c "$BRANCH" --track "origin/$BRANCH"
fi
git -C "$REPO" merge --ff-only "origin/$BRANCH"

ACTUAL_BRANCH="$(git -C "$REPO" branch --show-current)"
ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"
[[ "$ACTUAL_BRANCH" == "$BRANCH" ]] || fail "execution_branch_mismatch:$ACTUAL_BRANCH expected:$BRANCH"
[[ "$ACTUAL_HEAD" == "$EXPECTED_HEAD" ]] || fail "execution_head_mismatch:$ACTUAL_HEAD expected:$EXPECTED_HEAD"
[[ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]] || fail "product_repo_worktree_not_clean_after_ff:$REPO"

TMP_ROOT="$(mktemp -d "${TMPDIR:-${PREFIX:-/data/data/com.termux/files/usr}/tmp}/hpfa-reconstruction-intelligence.XXXXXX")" || fail "tempdir_create_failed"
cleanup(){ rm -rf "$TMP_ROOT"; }
trap cleanup EXIT INT TERM HUP
EVIDENCE="$TMP_ROOT/evidence"
mkdir -p "$EVIDENCE"

RUN_RC=0
set +e
(
  cd "$REPO"
  python reconstruction_intelligence_packet_adapter_current_v1.py \
    --input-dir "$ACTIVE_RESOLVED" \
    --out-dir "$EVIDENCE"
) >"$TMP_ROOT/reconstruction_intelligence_runtime.log" 2>&1
RUN_RC=$?
set -e

SEQUENCE_REPORT="$EVIDENCE/visible_action_sequence_candidates_lite_v1.json"
ADAPTER_REPORT="$EVIDENCE/reconstruction_intelligence_packet_adapter_lite_v1.json"
PACKET_REPORT="$EVIDENCE/composite_evidence_packet_builder_lite_v1.json"
BRIDGE_REPORT="$EVIDENCE/reconstruction_intelligence_packet_bridge_current_v1.json"
MANIFEST="$TMP_ROOT/HPFA_RECONSTRUCTION_INTELLIGENCE_PACKET_ACTIVE_MATCH_EVIDENCE_MANIFEST.json"
SUMMARY="$TMP_ROOT/HPFA_RECONSTRUCTION_INTELLIGENCE_PACKET_KISA_SONUC.txt"
ZIP="$OUT/HPFA_RECONSTRUCTION_INTELLIGENCE_PACKET_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.zip"
ZIP_TMP="$OUT/.HPFA_RECONSTRUCTION_INTELLIGENCE_PACKET_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.$$.zip.partial"
rm -f "$OUT"/HPFA_RECONSTRUCTION_INTELLIGENCE_PACKET_ACTIVE_MATCH_*.zip "$OUT"/.HPFA_RECONSTRUCTION_INTELLIGENCE_PACKET_ACTIVE_MATCH_*.zip.partial

python - "$SEQUENCE_REPORT" "$ADAPTER_REPORT" "$PACKET_REPORT" "$BRIDGE_REPORT" "$MANIFEST" "$SUMMARY" "$ACTUAL_BRANCH" "$ACTUAL_HEAD" "$ACTIVE_RESOLVED" "$RUN_RC" <<'PY'
import json
import sys
from pathlib import Path

seq_path, adapter_path, packet_path, bridge_path, manifest_path, summary_path = map(Path, sys.argv[1:7])
branch, head, runtime, run_rc_raw = sys.argv[7:11]
run_rc = int(run_rc_raw)

def load(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}

seq = load(seq_path)
adapter = load(adapter_path)
packet = load(packet_path)
bridge = load(bridge_path)

source_sequence_count = int(adapter.get("source_visible_action_sequence_candidate_count") or 0)
packet_input_count = int(adapter.get("packet_input_candidate_count") or 0)
composite_packet_count = int(packet.get("packet_count") or 0)
blocked_packet_count = int(packet.get("blocked_packet_count") or 0)
packet_rows = packet.get("packets") if isinstance(packet.get("packets"), list) else []

packet_contract_pass = bool(
    composite_packet_count == len(packet_rows)
    and composite_packet_count == packet_input_count
    and blocked_packet_count == 0
    and all(row.get("packet_family") == "sequence" for row in packet_rows)
    and all(row.get("claim_ceiling") == "composite_candidate_only" for row in packet_rows)
    and all(row.get("canonical_event_count") == "UNKNOWN" for row in packet_rows)
    and all(row.get("claim_output_allowed") is False for row in packet_rows)
    and all(row.get("report_language_allowed") is False for row in packet_rows)
)

partial_order_pass = bool(
    seq.get("same_timestamp_internal_ordering_allowed") is False
    and seq.get("source_row_order_is_temporal_truth") is False
    and seq.get("visible_sequence_candidate_is_sequence_truth") is False
    and seq.get("visible_sequence_candidate_is_possession_truth") is False
    and seq.get("single_team_continuity_is_control_truth") is False
    and seq.get("sequence_duration_is_physical_action_duration") is False
    and seq.get("sequence_truth") is False
    and seq.get("possession_truth") is False
    and seq.get("canonical_event_count") == "UNKNOWN"
    and seq.get("true_action_count") == "UNKNOWN"
    and seq.get("production_release") is False
)

adapter_boundary_pass = bool(
    adapter.get("packet_input_assignment_complete") is True
    and adapter.get("packet_input_ref_count_is_independent_source_count") is False
    and adapter.get("derived_reconstruction_refs_are_independent_sources") is False
    and adapter.get("independent_support_vote_allowed") is False
    and adapter.get("same_timestamp_internal_ordering_allowed") is False
    and adapter.get("source_row_order_is_temporal_truth") is False
    and adapter.get("visible_sequence_candidate_is_sequence_truth") is False
    and adapter.get("visible_sequence_candidate_is_possession_truth") is False
    and adapter.get("sequence_truth") is False
    and adapter.get("possession_truth") is False
    and adapter.get("causal_truth") is False
    and adapter.get("tactical_truth") is False
    and adapter.get("canonical_event_count") == "UNKNOWN"
    and adapter.get("true_action_count") == "UNKNOWN"
    and adapter.get("production_release") is False
    and not (adapter.get("hard_block_hits") or [])
)

active_pass = bool(
    run_rc == 0
    and seq.get("status") in {"PASS", "REVIEW_REQUIRED"}
    and seq.get("current_content_source_role_bridge_status") == "PASS"
    and adapter.get("status") in {"SMOKE_PASS", "REVIEW_REQUIRED"}
    and bridge.get("status") in {"SMOKE_PASS", "REVIEW_REQUIRED"}
    and source_sequence_count > 0
    and packet_input_count == source_sequence_count
    and packet_contract_pass
    and partial_order_pass
    and adapter_boundary_pass
    and not (bridge.get("hard_block_hits") or [])
    and bridge.get("canonical_event_count") == "UNKNOWN"
    and bridge.get("true_action_count") == "UNKNOWN"
    and bridge.get("production_release") is False
)

manifest = {
    "bundle_version": "HPFA_RECONSTRUCTION_INTELLIGENCE_PACKET_ACTIVE_MATCH_EVIDENCE_V1",
    "branch": branch,
    "head_sha": head,
    "runtime_authority": runtime,
    "run_rc": run_rc,
    "status": bridge.get("status") if active_pass else "FAIL_CLOSED",
    "runtime_evidence_status": "ACTIVE_MATCH_EVIDENCE_PASS" if active_pass else "FAIL_CLOSED",
    "active_match_evidence_pass": active_pass,
    "current_sequence_status": seq.get("status"),
    "content_source_role_bridge_status": seq.get("current_content_source_role_bridge_status"),
    "adapter_status": adapter.get("status"),
    "composite_packet_builder_status": packet.get("status"),
    "source_visible_action_sequence_candidate_count": source_sequence_count,
    "packet_input_candidate_count": packet_input_count,
    "review_required_packet_input_candidate_count": adapter.get("review_required_packet_input_candidate_count"),
    "composite_packet_count": composite_packet_count,
    "blocked_composite_packet_count": blocked_packet_count,
    "packet_input_assignment_complete": adapter.get("packet_input_assignment_complete"),
    "packet_contract_pass": packet_contract_pass,
    "partial_order_boundary_pass": partial_order_pass,
    "adapter_claim_boundary_pass": adapter_boundary_pass,
    "hard_block_hits": bridge.get("hard_block_hits") or [],
    "review_hits": bridge.get("review_hits") or [],
    "packet_input_ref_count_is_independent_source_count": False,
    "derived_reconstruction_refs_are_independent_sources": False,
    "independent_support_vote_allowed": False,
    "same_timestamp_internal_ordering_allowed": False,
    "source_row_order_is_temporal_truth": False,
    "visible_sequence_candidate_is_sequence_truth": False,
    "visible_sequence_candidate_is_possession_truth": False,
    "sequence_truth": False,
    "possession_truth": False,
    "causal_truth": False,
    "tactical_truth": False,
    "canonical_event_count": "UNKNOWN",
    "true_action_count": "UNKNOWN",
    "production_release": False,
}
Path(manifest_path).write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

lines = [
    "===================================================",
    "HPFA RECONSTRUCTION -> INTELLIGENCE KISA SONUÇ",
    "===================================================",
    f"branch={branch}",
    f"head_sha={head}",
    f"run_rc={run_rc}",
    f"status={manifest['status']}",
    f"active_match_evidence_pass={active_pass}",
    f"current_sequence_status={manifest['current_sequence_status']}",
    f"content_source_role_bridge_status={manifest['content_source_role_bridge_status']}",
    f"adapter_status={manifest['adapter_status']}",
    f"source_visible_action_sequence_candidate_count={source_sequence_count}",
    f"packet_input_candidate_count={packet_input_count}",
    f"composite_packet_count={composite_packet_count}",
    f"blocked_composite_packet_count={blocked_packet_count}",
    f"packet_input_assignment_complete={manifest['packet_input_assignment_complete']}",
    f"packet_contract_pass={packet_contract_pass}",
    f"partial_order_boundary_pass={partial_order_pass}",
    "independent_support_vote_allowed=false",
    "same_timestamp_internal_ordering_allowed=false",
    "source_row_order_is_temporal_truth=false",
    "visible_sequence_candidate_is_sequence_truth=false",
    "visible_sequence_candidate_is_possession_truth=false",
    "canonical_event_count=UNKNOWN",
    "true_action_count=UNKNOWN",
    "production_release=false",
    "===================================================",
]
Path(summary_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

ACTIVE_PASS="$(python - "$MANIFEST" <<'PY'
import json, sys
print("true" if json.load(open(sys.argv[1], encoding="utf-8")).get("active_match_evidence_pass") else "false")
PY
)"

if [[ "$ACTIVE_PASS" == "true" ]]; then
  python - "$EVIDENCE" "$MANIFEST" "$SUMMARY" "$TMP_ROOT/reconstruction_intelligence_runtime.log" "$ZIP_TMP" <<'PY'
import sys
import zipfile
from pathlib import Path

evidence = Path(sys.argv[1])
manifest = Path(sys.argv[2])
summary = Path(sys.argv[3])
log = Path(sys.argv[4])
out = Path(sys.argv[5])
with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(evidence.iterdir()):
        if path.is_file():
            zf.write(path, arcname=path.name)
    zf.write(manifest, arcname=manifest.name)
    zf.write(summary, arcname=summary.name)
    zf.write(log, arcname=log.name)
PY
  mv "$ZIP_TMP" "$ZIP"
else
  rm -f "$ZIP_TMP" "$ZIP"
fi

cat "$SUMMARY"
if [[ -f "$ZIP" ]]; then
  echo "ZIP=$ZIP"
else
  echo "ZIP=NOT_CREATED"
fi

[[ "$ACTIVE_PASS" == "true" ]] || exit 2
