from __future__ import annotations
from typing import Any

MODULE_ID="sequence_output_contract_guard_lite_v1"
CLAIM_SAFETY="SEQUENCE_OUTPUT_CONTRACT_GUARD_ONLY"
REQUIRED_OUTPUTS=["sequence_windows.csv","trace_variants.csv","consequence_map.csv","sequence_metric_candidates.csv","sequence_counter_scenarios.csv","sequence_engine_audit.json","sequence_decision.md"]

def _known_counts(counts: dict[str,Any] | None) -> bool:
    if not isinstance(counts,dict): return False
    for key,value in counts.items():
        try: amount=int(value)
        except Exception: amount=0
        if amount>0 and str(key).strip().lower() not in {"","unknown","unknown_or_other","none","null"}: return True
    return False

def _windows(report):
    items=report.get("event_windows") or report.get("event_windows_sample") or report.get("window_records") or []
    return [x for x in items if isinstance(x,dict)]

def _has_admitted_visible_time(report,windows):
    if str(report.get("time_admission_status") or report.get("time_field_admission_status") or "") != "ADMITTED": return False
    if str(report.get("time_axis_status") or "") != "AVAILABLE": return False
    if str(report.get("ordering_status") or "") != "VISIBLE_TIME_AVAILABLE": return False
    if str(report.get("ordering_authority") or "") != "PARTIAL_ORDER_ONLY": return False
    integrity=report.get("window_integrity_summary") or {}
    if integrity.get("downstream_ready") is not True: return False
    return any(str(w.get("window_axis"))=="minute" and w.get("temporal_admission") is True and w.get("time_semantic_admission") is True and w.get("source_row_order_is_temporal_truth") is not True and w.get("same_timestamp_internal_ordering_allowed") is not True for w in windows)

def sequence_contract_fields_present(report):
    windows=_windows(report)
    return {
      "canonical_action_id": bool(report.get("canonical_action_id_present") is True or any(w.get("canonical_action_id_present") is True or w.get("canonical_action_id_counts") for w in windows)),
      "timestamp_or_order": _has_admitted_visible_time(report,windows),
      "team_or_side": any(_known_counts(w.get("team_label_counts") or w.get("team_counts")) for w in windows),
      "canonical_family": any(_known_counts(w.get("action_family_counts") or w.get("canonical_family_counts")) for w in windows),
      "sequence_window_defined": bool(report.get("event_window_count",len(windows)) or windows),
      "claim_ceiling": bool(report.get("claim_safety") or report.get("claim_boundary") or any(w.get("claim_boundary") for w in windows)),
    }
def build_sequence_output_contract(report):
    fields=sequence_contract_fields_present(report); hits=[]
    mapping=[("canonical_action_id","canonical_action_id_missing"),("timestamp_or_order","timestamp_or_order_missing"),("team_or_side","team_or_side_missing"),("canonical_family","canonical_family_missing"),("sequence_window_defined","sequence_window_not_defined"),("claim_ceiling","claim_ceiling_missing")]
    for field,hit in mapping:
        if not fields[field]: hits.append(hit)
    return {"module_id":MODULE_ID,"claim_safety":CLAIM_SAFETY,"required_outputs_supported":REQUIRED_OUTPUTS,"required_fields_present":fields,"hard_block_hits":hits,"sequence_decision":"BLOCK_SEQUENCE_LAYER" if hits else "READY_FOR_SEQUENCE_CANDIDATE_CONSUMER","provenance_order_is_temporal_admission":False,"context_ordinal_is_temporal_admission":False,"event_index_is_temporal_admission":False,"same_timestamp_internal_ordering_allowed":False,"source_row_order_is_temporal_truth":False,"sequence_truth":False,"consequence_truth":False,"tactical_truth":False,"dominance_truth":False,"claim_output_allowed":False,"canonical_event_count":"UNKNOWN","true_action_count":"UNKNOWN","production_release":False,"claim_boundary":"sequence_output_contract_guard_only_no_sequence_truth"}
