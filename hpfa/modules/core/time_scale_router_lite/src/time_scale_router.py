from __future__ import annotations
import json,sys
from collections import defaultdict
from pathlib import Path
from typing import Any

MODULE_ID="time_scale_router_lite_v1"; CLAIM_SAFETY="TIME_SCALE_CANDIDATE_ONLY"; INPUT_JSON="event_window_builder_lite_v1.json"; OUTPUT_JSON="time_scale_router_lite_v1.json"; OUTPUT_TXT="time_scale_router_lite_v1.txt"
MIN_USABLE_DENSITY=5.0; MIN_USABLE_ROWS=25; MIN_LOW_DENSITY_ROWS=8; PROVENANCE_AXES={"context_ordinal","event_index"}

def repo_root_from_file(): return Path(__file__).resolve().parents[5]
def ensure_module_path(path):
    if str(path) not in sys.path: sys.path.insert(0,str(path))
def spine_runner_module(root):
    src=root/"hpfa"/"modules"/"core"/"active_match_spine_runner"/"src"; ensure_module_path(src); import spine_runner; return spine_runner
def safe_float(value):
    try:return float(str(value).replace(",","."))
    except (TypeError,ValueError):return 0.0
def safe_int(value):
    try:return int(float(str(value).replace(",",".")))
    except (TypeError,ValueError):return 0

def read_event_window_payload(input_dir):
    path=Path(input_dir).expanduser().resolve(strict=False)/INPUT_JSON
    if not path.exists(): return [],{"source_path":str(path),"input_read_status":"MISSING_INPUT","upstream_event_window_count":0,"loaded_window_count":0,"upstream_sample_truncated":False,"upstream_report":{}}
    data=json.loads(path.read_text(encoding="utf-8")); declared=safe_int(data.get("event_window_count",0)); full=data.get("event_windows")
    if isinstance(full,list): windows=list(full); truncated=False; status="FULL_WINDOWS_LOADED"
    else:
        sample=data.get("event_windows_sample",[]); windows=list(sample) if isinstance(sample,list) else []; truncated=declared>len(windows); status="UPSTREAM_SAMPLE_TRUNCATED" if truncated else "SAMPLE_WINDOWS_LOADED"
    meta={"source_path":str(path),"input_read_status":status,"upstream_event_window_count":declared or len(windows),"loaded_window_count":len(windows),"upstream_sample_truncated":truncated,
          "upstream_status":data.get("status"),"upstream_time_admission_status":data.get("time_admission_status") or data.get("time_field_admission_status"),"upstream_time_axis_status":data.get("time_axis_status"),"upstream_ordering_status":data.get("ordering_status"),"upstream_ordering_authority":data.get("ordering_authority"),"upstream_window_integrity_summary":data.get("window_integrity_summary") or {},"upstream_report":data}
    return windows,meta

def read_event_windows(input_dir):
    windows,meta=read_event_window_payload(input_dir); return [] if meta.get("upstream_sample_truncated") else windows

def _report_time_allowed(meta):
    return bool(meta.get("upstream_sample_truncated") is False and meta.get("upstream_status")=="PASS" and meta.get("upstream_time_admission_status")=="ADMITTED" and meta.get("upstream_time_axis_status")=="AVAILABLE" and meta.get("upstream_ordering_status")=="VISIBLE_TIME_AVAILABLE" and meta.get("upstream_ordering_authority")=="PARTIAL_ORDER_ONLY" and (meta.get("upstream_window_integrity_summary") or {}).get("downstream_ready") is True)

def route_window(window,upstream_time_allowed: bool | None=None):
    axis=str(window.get("window_axis","unknown")); rows=safe_int(window.get("surface_row_count")); density=safe_float(window.get("context_density")); confidence=str(window.get("window_confidence","unknown"))
    if upstream_time_allowed is None:
        upstream_time_allowed=bool(window.get("time_semantic_admission") is True and window.get("temporal_admission") is True)
    if axis=="minute" and upstream_time_allowed:
        if rows>=MIN_USABLE_ROWS and density>=MIN_USABLE_DENSITY: decision="MINUTE_AXIS_USABLE"; density_candidate="HIGH_SIGNAL_DENSITY"; reason="admitted_visible_minute_window_with_sufficient_surface_density"
        elif rows>=MIN_LOW_DENSITY_ROWS: decision="MINUTE_AXIS_LOW_DENSITY"; density_candidate="LOW_SIGNAL_DENSITY"; reason="admitted_visible_minute_window_with_low_surface_density"
        else: decision="TIME_SURFACE_INSUFFICIENT"; density_candidate="INSUFFICIENT_SIGNAL_DENSITY"; reason="admitted_visible_minute_window_but_insufficient_surface_rows"
        temporal=True; provenance=False; review=decision!="MINUTE_AXIS_USABLE"
    elif axis=="minute":
        decision="UPSTREAM_TIME_REVIEW_REQUIRED"; density_candidate="TIME_SEMANTIC_REVIEW_REQUIRED"; reason="minute_shape_without_report_level_time_semantic_admission"; temporal=False; provenance=False; review=True
    elif axis in PROVENANCE_AXES:
        decision="PROVENANCE_BUCKET_REVIEW_ONLY"; density_candidate="PROVENANCE_DENSITY_ONLY"; reason="list_or_source_position_is_provenance_only_not_football_time"; temporal=False; provenance=True; review=True
    else:
        decision="REVIEW_REQUIRED"; density_candidate="UNKNOWN_SIGNAL_DENSITY"; reason="unknown_or_unadmitted_window_axis"; temporal=False; provenance=False; review=True
    return {"window_id":str(window.get("window_id","unknown")),"window_axis":axis,"surface_row_count":rows,"context_density":density,"window_confidence":confidence,"time_scale_candidate":decision,"signal_density_candidate":density_candidate,"routing_decision":decision,"routing_reason":reason,"temporal_admission":temporal,"provenance_only":provenance,"review_required":review,"ordering_evidence_scope":"VISIBLE_MINUTE_BUCKET_ONLY" if temporal else "PROVENANCE_ORDER_ONLY","same_timestamp_internal_ordering_allowed":False,"source_row_order_is_temporal_truth":False,"terminal_action_surface_present":bool(window.get("terminal_action_surface_present")),"loss_recovery_surface_present":bool(window.get("loss_recovery_surface_present")),"restart_surface_present":bool(window.get("restart_surface_present")),"claim_allowed":False}
def route_windows(windows,upstream_time_allowed=False): return [route_window(w,upstream_time_allowed=upstream_time_allowed) for w in windows]
def summarize_routes(routed):
    dc=defaultdict(int); ac=defaultdict(int); den=defaultdict(int); terminal=loss=restart=temporal=provenance=review=0
    for i in routed:
        dc[str(i.get("routing_decision","unknown"))]+=1; ac[str(i.get("window_axis","unknown"))]+=1; den[str(i.get("signal_density_candidate","unknown"))]+=1; terminal+=int(bool(i.get("terminal_action_surface_present"))); loss+=int(bool(i.get("loss_recovery_surface_present"))); restart+=int(bool(i.get("restart_surface_present"))); temporal+=int(i.get("temporal_admission") is True); provenance+=int(i.get("provenance_only") is True); review+=int(i.get("review_required") is True)
    return {"routing_decision_counts":dict(sorted(dc.items())),"window_axis_counts":dict(sorted(ac.items())),"signal_density_candidate_counts":dict(sorted(den.items())),"terminal_action_routed_count":terminal,"loss_recovery_routed_count":loss,"restart_routed_count":restart,"temporal_admitted_window_count":temporal,"provenance_only_window_count":provenance,"review_required_routed_window_count":review}
def build_report(input_dir,root=None):
    repo_root=Path(root).resolve() if root is not None else repo_root_from_file(); windows,meta=read_event_window_payload(input_dir); truncated=meta.get("upstream_sample_truncated") is True; upstream_allowed=_report_time_allowed(meta); routed=[] if truncated else route_windows(windows,upstream_time_allowed=upstream_allowed); summary=summarize_routes(routed); axes=summary.get("window_axis_counts",{}); temporal=summary.get("temporal_admitted_window_count",0); admission="ADMITTED" if upstream_allowed and temporal>0 and not truncated else "REVIEW_REQUIRED"
    return {"module_id":MODULE_ID,"status":"PASS" if admission=="ADMITTED" else "REVIEW_REQUIRED","decision":"UPSTREAM_SAMPLE_TRUNCATED" if truncated else "TIME_SCALE_CANDIDATES_ONLY","claim_safety":CLAIM_SAFETY,"input_window_count":len(windows),"routed_window_count":len(routed),"minute_axis_window_count":axes.get("minute",0),"context_ordinal_window_count":axes.get("context_ordinal",0),"event_index_window_count":axes.get("event_index",0),"provenance_only_window_count":summary.get("provenance_only_window_count",0),"temporal_admitted_window_count":temporal,"review_required_routed_window_count":summary.get("review_required_routed_window_count",0),"routed_windows":routed,"routed_windows_sample":routed[:200],"routing_summary":summary,"input_meta":{k:v for k,v in meta.items() if k!="upstream_report"},"time_admission_status":admission,"upstream_time_admission_status":meta.get("upstream_time_admission_status"),"upstream_time_allowed":upstream_allowed,"downstream_time_allowed":admission=="ADMITTED","downstream_sequence_time_allowed":admission=="ADMITTED","downstream_phase_time_allowed":admission=="ADMITTED","downstream_rhythm_time_allowed":admission=="ADMITTED","ordering_authority":"PARTIAL_ORDER_ONLY","same_timestamp_internal_ordering_allowed":False,"source_row_order_is_temporal_truth":False,"canonical_event_count":"UNKNOWN","deduplicated_event_count":"UNKNOWN","true_action_count":"UNKNOWN","phase_truth":False,"possession_truth":False,"sequence_truth":False,"rhythm_truth":False,"time_window_truth":False,"tactical_truth":False,"dominance_truth":False,"claim_allowed":False,"production_release":False,"input_dir":str(Path(input_dir).expanduser().resolve(strict=False)),"repo_root":str(repo_root)}
def render_txt(report):
    return "\n".join(["HPFA TIME-SCALE ROUTER LITE V1","================================",f"status={report.get('status')}",f"time_admission_status={report.get('time_admission_status')}",f"routed_window_count={report.get('routed_window_count')}",f"temporal_admitted_window_count={report.get('temporal_admitted_window_count')}",f"downstream_time_allowed={report.get('downstream_time_allowed')}","canonical_event_count=UNKNOWN","true_action_count=UNKNOWN","production_release=false",""])
def write_outputs(input_dir,out_dir,root=None):
    repo_root=Path(root).resolve() if root is not None else repo_root_from_file(); spine=spine_runner_module(repo_root); output_root=spine.validate_output_root(out_dir); output_root.mkdir(parents=True,exist_ok=True); report=build_report(input_dir,root=repo_root); json_out=output_root/OUTPUT_JSON; txt_out=output_root/OUTPUT_TXT; report["outputs"]={"json":str(json_out),"txt":str(txt_out)}; json_out.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8"); txt_out.write_text(render_txt(report),encoding="utf-8"); return report
