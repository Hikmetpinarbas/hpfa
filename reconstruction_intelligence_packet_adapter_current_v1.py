from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import visible_action_sequence_candidates_current_v1 as current_sequence
from hpfa.modules.core.composite_evidence_packet_builder_lite.src import composite_evidence_packet_builder as packet_builder
from hpfa.modules.core.reconstruction_intelligence_packet_adapter_lite.src import reconstruction_intelligence_packet_adapter as adapter

MODULE_ID = "reconstruction_intelligence_packet_bridge_current_v1"
OUTPUT_JSON = "reconstruction_intelligence_packet_bridge_current_v1.json"
OUTPUT_TXT = "reconstruction_intelligence_packet_bridge_current_v1.txt"

# These files are owned by the reconstruction invocation that starts at
# current_sequence and walks the existing current C1→C2→C3 wrappers. Clearing
# them before any fallible input I/O lets presence after the run function as a
# producer write ledger even when deterministic content is byte-identical to the
# preceding invocation.
RECONSTRUCTION_OWNED_OUTPUTS = {
    "row_nucleus_inventory_lite_v1.json",
    "row_nucleus_inventory_lite_v1.txt",
    "row_nucleus_analyst_audit_v1.txt",
    "evidence_atom_inventory_lite_v1.json",
    "evidence_atom_inventory_lite_v1.txt",
    "evidence_atom_analyst_audit_v1.txt",
    "match_local_identity_candidates_lite_v1.json",
    "match_local_identity_candidates_lite_v1.txt",
    "match_local_identity_analyst_audit_v1.txt",
    "semantic_role_action_bundle_candidates_lite_v1.json",
    "semantic_role_action_bundle_candidates_lite_v1.txt",
    "semantic_role_action_bundle_analyst_audit_v1.txt",
    "action_bundle_multi_family_review_taxonomy_lite_v1.json",
    "action_bundle_multi_family_review_taxonomy_lite_v1.txt",
    "action_bundle_multi_family_review_taxonomy_analyst_audit_v1.txt",
    "cross_role_relation_candidate_resolver_lite_v1.json",
    "cross_role_relation_candidate_resolver_lite_v1.txt",
    "cross_role_relation_candidate_resolver_analyst_audit_v1.txt",
    "trackable_action_trace_candidates_lite_v1.json",
    "trackable_action_trace_candidates_lite_v1.txt",
    "trackable_action_trace_candidates_analyst_audit_v1.txt",
    "trackable_action_consequence_candidates_lite_v1.json",
    "trackable_action_consequence_candidates_lite_v1.txt",
    "trackable_action_consequence_candidates_analyst_audit_v1.txt",
    "visible_action_sequence_candidates_lite_v1.json",
    "visible_action_sequence_candidates_lite_v1.txt",
    "visible_action_sequence_candidates_analyst_audit_v1.txt",
    "reconstruction_intelligence_packet_adapter_lite_v1.json",
    "reconstruction_intelligence_packet_adapter_lite_v1.txt",
    "composite_evidence_packet_builder_lite_v1.json",
    "composite_evidence_packet_builder_lite_v1.txt",
    "g01_g18_data_quality_rollup_v1.json",
    "g01_g18_data_quality_rollup_v1.txt",
}


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _surface_snapshot(input_dir: str | Path) -> dict:
    root = Path(input_dir).expanduser().resolve(strict=False)
    records: list[dict] = []
    if root.is_dir():
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().casefold()):
            if not path.is_file():
                continue
            records.append({
                "relative_path": path.relative_to(root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": _hash_file(path),
            })
    stable_payload = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "snapshot_id": hashlib.sha256(stable_payload.encode("utf-8")).hexdigest(),
        "surface_file_count": len(records),
        "records": records,
    }


def _clear_reconstruction_owned_outputs(output: Path) -> list[str]:
    cleared: list[str] = []
    for name in sorted(RECONSTRUCTION_OWNED_OUTPUTS):
        path = output / name
        if not path.is_file():
            continue
        path.unlink()
        cleared.append(name)
    return cleared


def _current_reconstruction_owned_outputs(output: Path) -> list[str]:
    return [
        str(output / name)
        for name in sorted(RECONSTRUCTION_OWNED_OUTPUTS)
        if (output / name).is_file()
    ]


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _collect_output_paths(*payloads: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for payload in payloads:
        inherited = payload.get("current_invocation_artifacts")
        if isinstance(inherited, list):
            values.extend(str(value or "") for value in inherited)
        outputs = payload.get("outputs")
        if isinstance(outputs, dict):
            values.extend(str(value or "") for value in outputs.values())
    return _dedupe_preserve_order(values)


def _first_packet_builder_hard_block(packet_report: dict[str, Any]) -> str | None:
    direct = packet_report.get("hard_block_hits") or []
    if isinstance(direct, list) and direct:
        return str(direct[0])
    for packet in packet_report.get("packets") or []:
        if not isinstance(packet, dict):
            continue
        reasons = packet.get("hard_block_hits") or packet.get("blocked_reasons") or []
        if isinstance(reasons, list) and reasons:
            return str(reasons[0])
    return None


def _write_bridge_report(report: dict, output: Path) -> None:
    json_path = output / OUTPUT_JSON
    txt_path = output / OUTPUT_TXT
    report["outputs"] = {
        **dict(report.get("outputs") or {}),
        "bridge_json": str(json_path),
        "bridge_txt": str(txt_path),
    }
    declared = list(report.get("current_invocation_artifacts") or [])
    for path in (json_path, txt_path):
        text = str(path)
        if text not in declared:
            declared.append(text)
    report["current_invocation_artifacts"] = declared
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "HPFA RECONSTRUCTION -> INTELLIGENCE PACKET BRIDGE CURRENT V1",
        "============================================================",
        f"status={report.get('status')}",
        f"current_sequence_status={report.get('current_sequence_status')}",
        f"adapter_status={report.get('adapter_status')}",
        f"input_surface_snapshot_id={report.get('input_surface_snapshot_id')}",
        f"input_surface_snapshot_file_count={report.get('input_surface_snapshot_file_count')}",
        f"input_surface_snapshot_stable={report.get('input_surface_snapshot_stable')}",
        f"source_visible_action_sequence_candidate_count={report.get('source_visible_action_sequence_candidate_count')}",
        f"packet_input_candidate_count={report.get('packet_input_candidate_count')}",
        f"composite_packet_count={report.get('composite_packet_count')}",
        f"blocked_composite_packet_count={report.get('blocked_composite_packet_count')}",
        f"review_required_packet_input_candidate_count={report.get('review_required_packet_input_candidate_count')}",
        f"packet_input_assignment_complete={report.get('packet_input_assignment_complete')}",
        f"current_invocation_artifact_count={len(report.get('current_invocation_artifacts') or [])}",
        f"cleared_stale_reconstruction_owned_output_count={len(report.get('cleared_stale_reconstruction_owned_outputs') or [])}",
        f"hard_block_hits={report.get('hard_block_hits') or []}",
        f"review_hits={report.get('review_hits') or []}",
        "independent_support_vote_allowed=false",
        "same_timestamp_internal_ordering_allowed=false",
        "source_row_order_is_temporal_truth=false",
        "visible_sequence_candidate_is_sequence_truth=false",
        "visible_sequence_candidate_is_possession_truth=false",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
        "",
    ]
    txt_path.write_text("\n".join(lines), encoding="utf-8")


def runtime_write_outputs(input_dir: str | Path, out_dir: str | Path) -> dict:
    output = adapter.validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    cleared_outputs = _clear_reconstruction_owned_outputs(output)

    snapshot_before = _surface_snapshot(input_dir)
    sequence_payload = current_sequence.runtime_write_outputs(input_dir, output)
    snapshot_after = _surface_snapshot(input_dir)
    snapshot_stable = (
        snapshot_before.get("snapshot_id") == snapshot_after.get("snapshot_id")
        and snapshot_before.get("surface_file_count") == snapshot_after.get("surface_file_count")
    )

    hard_blocks: list[str] = []
    adapter_report: dict = {
        "status": "NOT_EVALUATED",
        "composite_packet_input_candidates": [],
        "hard_block_hits": [],
        "review_hits": [],
    }
    if not snapshot_stable:
        hard_blocks.append("active_match_surface_snapshot_changed_during_reconstruction")
    else:
        adapter_report = adapter.write_outputs(sequence_payload, output)
        hard_blocks.extend(str(item) for item in (adapter_report.get("hard_block_hits") or []))

    packet_report: dict = {
        "status": "NOT_EVALUATED",
        "packet_count": 0,
        "blocked_packet_count": 0,
        "packets": [],
    }
    if not hard_blocks and adapter_report.get("status") != "FAIL_CLOSED":
        packet_report = packet_builder.write_outputs(
            list(adapter_report.get("composite_packet_input_candidates") or []),
            output,
        )
        if packet_report.get("status") == "FAIL_CLOSED":
            hard_blocks.append(
                _first_packet_builder_hard_block(packet_report)
                or "composite_packet_builder_failed_closed"
            )

    hard_blocks = _dedupe_preserve_order(hard_blocks)
    if hard_blocks:
        status = "FAIL_CLOSED"
    elif adapter_report.get("status") == "REVIEW_REQUIRED":
        status = "REVIEW_REQUIRED"
    else:
        status = "SMOKE_PASS"

    owned_artifacts = _current_reconstruction_owned_outputs(output)
    current_artifacts = _dedupe_preserve_order([
        *_collect_output_paths(sequence_payload, adapter_report, packet_report),
        *owned_artifacts,
    ])
    report = {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "active_match_evidence_pass": False,
        "current_sequence_status": sequence_payload.get("status"),
        "adapter_status": adapter_report.get("status"),
        "composite_packet_builder_status": packet_report.get("status"),
        "input_surface_snapshot_id": snapshot_before.get("snapshot_id"),
        "input_surface_snapshot_file_count": snapshot_before.get("surface_file_count"),
        "input_surface_snapshot_stable": snapshot_stable,
        "input_surface_snapshot_changed": not snapshot_stable,
        "match_surface_binding_id": adapter_report.get("match_surface_binding_id"),
        "source_visible_action_sequence_candidate_count": adapter_report.get("source_visible_action_sequence_candidate_count"),
        "packet_input_candidate_count": adapter_report.get("packet_input_candidate_count"),
        "review_required_packet_input_candidate_count": adapter_report.get("review_required_packet_input_candidate_count"),
        "packet_input_assignment_complete": adapter_report.get("packet_input_assignment_complete"),
        "composite_packet_count": packet_report.get("packet_count"),
        "blocked_composite_packet_count": packet_report.get("blocked_packet_count"),
        "cleared_stale_reconstruction_owned_outputs": cleared_outputs,
        "current_invocation_artifacts": current_artifacts,
        "hard_block_hits": hard_blocks,
        "review_hits": list(adapter_report.get("review_hits") or []),
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
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    _write_bridge_report(report, output)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="HPFA current Reconstruction to Intelligence packet bridge")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    report = runtime_write_outputs(args.input_dir, args.out_dir)
    print(json.dumps({
        "status": report.get("status"),
        "current_sequence_status": report.get("current_sequence_status"),
        "adapter_status": report.get("adapter_status"),
        "input_surface_snapshot_id": report.get("input_surface_snapshot_id"),
        "input_surface_snapshot_stable": report.get("input_surface_snapshot_stable"),
        "source_visible_action_sequence_candidate_count": report.get("source_visible_action_sequence_candidate_count"),
        "packet_input_candidate_count": report.get("packet_input_candidate_count"),
        "composite_packet_count": report.get("composite_packet_count"),
        "blocked_composite_packet_count": report.get("blocked_composite_packet_count"),
        "packet_input_assignment_complete": report.get("packet_input_assignment_complete"),
        "current_invocation_artifact_count": len(report.get("current_invocation_artifacts") or []),
        "hard_block_hits": report.get("hard_block_hits") or [],
        "review_hits": report.get("review_hits") or [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if report.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
