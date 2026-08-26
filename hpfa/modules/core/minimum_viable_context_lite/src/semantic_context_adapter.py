
from __future__ import annotations
from typing import Any
MODULE_ID="semantic_context_adapter_lite_v1"
CANONICAL_TO_CONTEXT_KEY={
 "event.action":"event_type","event.team":"team","event.player":"player","event.minute":"minute","event.second":"second","event.period":"period",
 "event.start_x":"x","event.start_y":"y","event.end_x":"end_x","event.end_y":"end_y","event.source_file":"_source_file",
}
ABSOLUTE_SECOND_CONTEXT_KEYS={"absolute_time_seconds":"absolute_time_seconds","match_second":"match_second"}
COMPONENT_SECOND_SOURCE_KEYS={"second","seconds","second_raw"}
def _norm(value): return str(value or "").strip().lower().replace(" ","_")
def _time_target(source, normalized=None):
    value=_norm(normalized or source)
    if value in ABSOLUTE_SECOND_CONTEXT_KEYS: return ABSOLUTE_SECOND_CONTEXT_KEYS[value]
    if value in COMPONENT_SECOND_SOURCE_KEYS: return "second"
    return None
def build_column_map(field_surface,mapping_report=None):
    column_map={}
    for record in (mapping_report or {}).get("mapping_records",[]) or []:
        canonical=record.get("canonical_key_candidate"); source=record.get("source_column")
        time_target=_time_target(source)
        if time_target and source: column_map[str(source)]=time_target
        elif canonical in CANONICAL_TO_CONTEXT_KEY and source: column_map[str(source)]=CANONICAL_TO_CONTEXT_KEY[str(canonical)]
    for record in field_surface.get("field_semantic_records",[]) or []:
        source=record.get("source_column"); normalized=_norm(record.get("normalized_column") or source); canonical=record.get("canonical_key") or record.get("canonical_key_candidate")
        time_target=_time_target(source, normalized)
        if time_target and source:
            column_map[str(source)]=time_target
        elif canonical in CANONICAL_TO_CONTEXT_KEY and source:
            column_map.setdefault(str(source),CANONICAL_TO_CONTEXT_KEY[str(canonical)])
        elif normalized in {"event_type","action","type"} and source: column_map.setdefault(str(source),"event_type")
        elif normalized in {"team","team_id","team_name"} and source: column_map.setdefault(str(source),"team")
        elif normalized in {"minute","minutes","minute_raw","match_minute"} and source: column_map.setdefault(str(source),"minute")
        elif normalized in {"period","half"} and source: column_map.setdefault(str(source),"period")
        elif normalized in {"x","start_x","pos_x"} and source: column_map.setdefault(str(source),"x")
        elif normalized in {"y","start_y","pos_y"} and source: column_map.setdefault(str(source),"y")
        # Generic time/timestamp/start/end remain preserved until explicit canonical role+unit admission.
    return column_map
def adapt_rows(rows,field_surface,mapping_report=None):
    column_map=build_column_map(field_surface,mapping_report); adapted=[]; unmapped_columns=set()
    for idx,row in enumerate(rows):
        out={"_source_row_index":row.get("_source_row_index",idx),"_semantic_adapter_runtime_verified":False}
        for key,value in row.items():
            target=column_map.get(key)
            if target: out[target]=value
            else: unmapped_columns.add(str(key)); out.setdefault("_preserved_unmapped",{})[str(key)]=value
        adapted.append(out)
    return {"module_id":MODULE_ID,"status":"REVIEW_REQUIRED" if unmapped_columns else "SMOKE_PASS","runtime_verified":False,
      "adapted_row_count":len(adapted),"column_map":column_map,"unmapped_columns":sorted(unmapped_columns),"rows":adapted,
      "claim_boundary":"semantic_context_adapter_candidate_only","generic_numeric_time_is_temporal_truth":False,
      "canonical_event_count":"UNKNOWN","production_release":False}