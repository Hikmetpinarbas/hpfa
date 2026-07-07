from __future__ import annotations

from typing import Any

MODULE_ID = "sequence_output_contract_guard_lite_v1"
CLAIM_SAFETY = "SEQUENCE_OUTPUT_CONTRACT_GUARD_ONLY"

REQUIRED_OUTPUTS = [
    "sequence_windows.csv",
    "trace_variants.csv",
    "consequence_map.csv",
    "sequence_metric_candidates.csv",
    "sequence_counter_scenarios.csv",
    "sequence_engine_audit.json",
    "sequence_decision.md",
]

HARD_BLOCKS = [
    "canonical_action_id_missing",
    "timestamp_or_order_missing",
    "team_or_side_missing",
    "canonical_family_missing",
    "sequence_window_not_defined",
    "claim_ceiling_missing",
]


def _known_counts(counts: dict[str, Any] | None) -> bool:
    if not isinstance(counts, dict):
        return False
    for key, value in counts.items():
        label = str(key).strip().lower()
        try:
            amount = int(value)
        except Exception:
            amount = 0
        if amount > 0 and label not in {"", "unknown", "unknown_or_other", "none", "null"}:
            return True
    return False


def _windows(report: dict[str, Any]) -> list[dict[str, Any]]:
    items = report.get("event_windows_sample") or report.get("window_records") or []
    return [item for item in items if isinstance(item, dict)]


def sequence_contract_fields_present(report: dict[str, Any]) -> dict[str, bool]:
    windows = _windows(report)
    has_order = bool(
        report.get("time_axis_status") != "MISSING"
        or report.get("index_window_enabled") is True
        or any(win.get("window_axis") in {"minute", "context_ordinal", "event_index"} for win in windows)
    )
    has_team = any(_known_counts(win.get("team_label_counts") or win.get("team_counts")) for win in windows)
    has_family = any(_known_counts(win.get("action_family_counts") or win.get("canonical_family_counts")) for win in windows)
    has_sequence_window = bool(report.get("event_window_count", len(windows)) or windows)
    has_claim_ceiling = bool(report.get("claim_safety") or report.get("claim_boundary") or any(win.get("claim_boundary") for win in windows))
    has_canonical_action_id = bool(
        report.get("canonical_action_id_present") is True
        or any(win.get("canonical_action_id_present") is True or win.get("canonical_action_id_counts") for win in windows)
    )
    return {
        "canonical_action_id": has_canonical_action_id,
        "timestamp_or_order": has_order,
        "team_or_side": has_team,
        "canonical_family": has_family,
        "sequence_window_defined": has_sequence_window,
        "claim_ceiling": has_claim_ceiling,
    }


def build_sequence_output_contract(report: dict[str, Any]) -> dict[str, Any]:
    fields = sequence_contract_fields_present(report)
    hard_block_hits = []
    if not fields["canonical_action_id"]:
        hard_block_hits.append("canonical_action_id_missing")
    if not fields["timestamp_or_order"]:
        hard_block_hits.append("timestamp_or_order_missing")
    if not fields["team_or_side"]:
        hard_block_hits.append("team_or_side_missing")
    if not fields["canonical_family"]:
        hard_block_hits.append("canonical_family_missing")
    if not fields["sequence_window_defined"]:
        hard_block_hits.append("sequence_window_not_defined")
    if not fields["claim_ceiling"]:
        hard_block_hits.append("claim_ceiling_missing")

    return {
        "module_id": MODULE_ID,
        "claim_safety": CLAIM_SAFETY,
        "required_outputs_supported": REQUIRED_OUTPUTS,
        "required_fields_present": fields,
        "hard_block_hits": hard_block_hits,
        "sequence_decision": "BLOCK_SEQUENCE_LAYER" if hard_block_hits else "READY_FOR_SEQUENCE_CANDIDATE_CONSUMER",
        "sequence_truth": False,
        "consequence_truth": False,
        "tactical_truth": False,
        "dominance_truth": False,
        "claim_output_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "claim_boundary": "sequence_output_contract_guard_only_no_sequence_truth",
    }
