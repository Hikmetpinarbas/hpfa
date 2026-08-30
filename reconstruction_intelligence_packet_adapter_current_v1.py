from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import visible_action_sequence_candidates_current_v1 as current_sequence
from hpfa.modules.core.composite_evidence_packet_builder_lite.src import composite_evidence_packet_builder as packet_builder
from hpfa.modules.core.reconstruction_intelligence_packet_adapter_lite.src import reconstruction_intelligence_packet_adapter as adapter

MODULE_ID = "reconstruction_intelligence_packet_bridge_current_v1"
OUTPUT_JSON = "reconstruction_intelligence_packet_bridge_current_v1.json"
OUTPUT_TXT = "reconstruction_intelligence_packet_bridge_current_v1.txt"


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


def _write_bridge_report(report: dict, output: Path) -> None:
    json_path = output / OUTPUT_JSON
    txt_path = output / OUTPUT_TXT
    report["outputs"] = {
        **dict(report.get("outputs") or {}),
        "bridge_json": str(json_path),
        "bridge_txt": str(txt_path),
    }
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
        hard_blocks.extend(adapter_report.get("hard_block_hits") or [])

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
            hard_blocks.append("composite_packet_builder_failed_closed")

    if hard_blocks:
        status = "FAIL_CLOSED"
    elif adapter_report.get("status") == "REVIEW_REQUIRED":
        status = "REVIEW_REQUIRED"
    else:
        status = "SMOKE_PASS"

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
        "hard_block_hits": sorted(set(str(item) for item in hard_blocks)),
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
        "hard_block_hits": report.get("hard_block_hits") or [],
        "review_hits": report.get("review_hits") or [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if report.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
