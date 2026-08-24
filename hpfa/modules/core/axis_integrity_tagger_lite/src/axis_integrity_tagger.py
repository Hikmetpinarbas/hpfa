from __future__ import annotations
import json,sys
from pathlib import Path
from typing import Any
MODULE_ID="axis_integrity_tagger_lite_v1"; CLAIM_SAFETY="AXIS_INTEGRITY_CANDIDATE_ONLY"; OUTPUT_JSON="axis_integrity_tagger_lite_v1.json"; OUTPUT_TXT="axis_integrity_tagger_lite_v1.txt"; TIME_ROUTER_JSON="time_scale_router_lite_v1.json"; EVENT_WINDOW_JSON="event_window_builder_lite_v1.json"; MIN_CONTEXT_JSON="minimum_viable_context_lite_v1.json"
AVAILABLE="AXIS_AVAILABLE"; PARTIAL="AXIS_PARTIAL"; MISSING="AXIS_MISSING"; UNKNOWN="AXIS_UNKNOWN"
def repo_root_from_file(): return Path(__file__).resolve().parents[5]
def ensure_module_path(path):
    if str(path) not in sys.path: sys.path.insert(0,str(path))
def spine_runner_module(root):
    src=root/"hpfa"/"modules"/"core"/"active_match_spine_runner"/"src"; ensure_module_path(src); import spine_runner; return spine_runner
def read_json(path):
    if not path.exists(): return {}
    try:data=json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:return {}
    return data if isinstance(data,dict) else {}
def safe_int(value):
    try:return int(float(str(value).replace(",",".")))
    except (TypeError,ValueError):return 0
def status_score(status): return 1.0 if status==AVAILABLE else 0.5 if status==PARTIAL else 0.0
def rows_from(payload,full_key,sample_key):
    rows=payload.get(full_key); rows=rows if isinstance(rows,list) else payload.get(sample_key); return [x for x in rows if isinstance(x,dict)] if isinstance(rows,list) else []
def has_value(value): return value not in (None,"","unknown","UNKNOWN","UNKNOWN_ZONE","UNKNOWN_CHANNEL")
def count_rows_with_keys(rows,keys): return sum(1 for row in rows if any(has_value(row.get(k)) for k in keys))
def count_rows_with_count_dict(rows,keys):
    count=0
    for row in rows:
        if any(isinstance(row.get(k),dict) and any(safe_int(v)>0 for v in row.get(k).values()) for k in keys): count+=1
    return count
def ratio_status(count,total,empty_status=UNKNOWN):
    if total<=0:return empty_status
    ratio=count/total
    return AVAILABLE if ratio>=0.75 else PARTIAL if ratio>0 else MISSING
def axis_from_context_or_windows(contexts,windows,context_keys,window_count_keys):
    status=ratio_status(count_rows_with_keys(contexts,context_keys),len(contexts)); return status if status!=UNKNOWN else ratio_status(count_rows_with_count_dict(windows,window_count_keys),len(windows))
def build_axis_report(input_dir):
    root=Path(input_dir).expanduser().resolve(strict=False); tsr=read_json(root/TIME_ROUTER_JSON); ewb=read_json(root/EVENT_WINDOW_JSON); mvc=read_json(root/MIN_CONTEXT_JSON); contexts=rows_from(mvc,"context_candidates","context_candidates_sample"); windows=rows_from(ewb,"event_windows","event_windows_sample")
    routed=safe_int(tsr.get("routed_window_count")); router_time_allowed=tsr.get("downstream_time_allowed") is True; router_admission=str(tsr.get("time_admission_status") or "REVIEW_REQUIRED"); ewb_admission=str(ewb.get("time_admission_status") or ewb.get("time_field_admission_status") or "REVIEW_REQUIRED"); ewb_time=str(ewb.get("time_axis_status") or "MISSING"); ewb_order=str(ewb.get("ordering_status") or "ORDER_INDETERMINATE")
    semantic_time_admitted=bool(router_time_allowed and router_admission=="ADMITTED" and ewb_admission=="ADMITTED" and ewb_time=="AVAILABLE" and ewb_order=="VISIBLE_TIME_AVAILABLE")
    minute_status=AVAILABLE if semantic_time_admitted else MISSING
    event_index_status=AVAILABLE if safe_int(tsr.get("event_index_window_count"))>0 else MISSING
    second_status=ratio_status(count_rows_with_keys(contexts,["second","seconds","second_raw","match_second"]),len(contexts))
    space_status=axis_from_context_or_windows(contexts,windows,["x_meters","y_meters","x_raw","y_raw","zone_candidate","channel_candidate"],["zone_counts","channel_counts"])
    team_status=axis_from_context_or_windows(contexts,windows,["team_label","team_raw","team_normalized"],["team_label_counts"])
    action_status=axis_from_context_or_windows(contexts,windows,["action_family","event_family","event_type_raw"],["action_family_counts"])
    statuses=[minute_status,second_status,event_index_status,space_status,team_status,action_status]; score=round(sum(status_score(s) for s in statuses)/len(statuses),4)
    time_allowed=semantic_time_admitted; phase_allowed=time_allowed and space_status in {AVAILABLE,PARTIAL} and action_status in {AVAILABLE,PARTIAL}; sequence_allowed=time_allowed and team_status in {AVAILABLE,PARTIAL} and action_status in {AVAILABLE,PARTIAL}; rhythm_allowed=time_allowed and routed>0
    reasons=[]
    if not semantic_time_admitted: reasons.append("upstream_time_semantics_not_admitted")
    return {"module_id":MODULE_ID,"status":"PASS" if semantic_time_admitted else "REVIEW_REQUIRED","decision":"AXIS_INTEGRITY_CANDIDATES_ONLY","claim_safety":CLAIM_SAFETY,"input_dir":str(root),"input_counts":{"context_sample_count":len(contexts),"event_window_sample_count":len(windows),"routed_window_count":routed},"axis_status":{"minute_axis_status":minute_status,"second_axis_status":second_status,"event_index_axis_status":event_index_status,"space_axis_status":space_status,"team_axis_status":team_status,"action_family_axis_status":action_status},"minute_axis_admission_status":"ADMITTED" if semantic_time_admitted else "REVIEW_REQUIRED","time_permission_basis":{"router_downstream_time_allowed":router_time_allowed,"router_time_admission_status":router_admission,"event_window_time_admission_status":ewb_admission,"event_window_time_axis_status":ewb_time,"event_window_ordering_status":ewb_order},"permission_contraction_reasons":reasons,"axis_integrity_score":score,"downstream_permissions":{"downstream_time_allowed":time_allowed,"downstream_phase_candidate_allowed":phase_allowed,"downstream_sequence_candidate_allowed":sequence_allowed,"downstream_rhythm_candidate_allowed":rhythm_allowed},"canonical_event_count":"UNKNOWN","deduplicated_event_count":"UNKNOWN","true_action_count":"UNKNOWN","phase_truth":False,"possession_truth":False,"sequence_truth":False,"rhythm_truth":False,"time_window_truth":False,"tactical_truth":False,"dominance_truth":False,"claim_allowed":False,"production_release":False}
def render_txt(report):
    return "\n".join(["HPFA AXIS INTEGRITY TAGGER LITE V1","===================================",f"status={report.get('status')}",f"axis_integrity_score={report.get('axis_integrity_score')}",f"minute_axis_admission_status={report.get('minute_axis_admission_status')}",f"downstream_permissions={json.dumps(report.get('downstream_permissions',{}),sort_keys=True)}","canonical_event_count=UNKNOWN","true_action_count=UNKNOWN","production_release=false",""])
def write_outputs(input_dir,out_dir,root=None):
    repo_root=Path(root).resolve() if root is not None else repo_root_from_file(); spine=spine_runner_module(repo_root); output_root=spine.validate_output_root(out_dir); output_root.mkdir(parents=True,exist_ok=True); report=build_axis_report(input_dir); json_out=output_root/OUTPUT_JSON; txt_out=output_root/OUTPUT_TXT; report["outputs"]={"json":str(json_out),"txt":str(txt_out)}; json_out.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8"); txt_out.write_text(render_txt(report),encoding="utf-8"); return report
