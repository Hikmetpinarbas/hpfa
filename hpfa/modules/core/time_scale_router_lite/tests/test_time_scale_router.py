import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]; SRC=ROOT/'hpfa/modules/core/time_scale_router_lite/src'; sys.path.insert(0,str(SRC))
from time_scale_router import build_report,route_window,write_outputs

def base_window(**kw):
 d={'window_id':'w','window_axis':'minute','surface_row_count':30,'context_density':6.0,'window_confidence':'high','temporal_admission':True,'time_semantic_admission':True,'source_row_order_is_temporal_truth':False,'same_timestamp_internal_ordering_allowed':False}; d.update(kw); return d
def write_payload(path,windows,admitted=True):
 path.write_text(json.dumps({'module_id':'event_window_builder_lite_v1','status':'PASS' if admitted else 'REVIEW_REQUIRED','event_window_count':len(windows),'event_windows_sample':windows,'time_admission_status':'ADMITTED' if admitted else 'REVIEW_REQUIRED','time_axis_status':'AVAILABLE' if admitted else 'MISSING','ordering_status':'VISIBLE_TIME_AVAILABLE' if admitted else 'ORDER_INDETERMINATE','ordering_authority':'PARTIAL_ORDER_ONLY','window_integrity_summary':{'downstream_ready':admitted}}))
def test_route_direct_minute_usable(): assert route_window(base_window())['routing_decision']=='MINUTE_AXIS_USABLE'
def test_provenance_review_only(): assert route_window(base_window(window_axis='context_ordinal',temporal_admission=False,time_semantic_admission=False))['routing_decision']=='PROVENANCE_BUCKET_REVIEW_ONLY'
def test_report_admitted_time(tmp_path):
 write_payload(tmp_path/'event_window_builder_lite_v1.json',[base_window()],True); r=build_report(tmp_path,root=ROOT); assert r['time_admission_status']=='ADMITTED'; assert r['downstream_time_allowed'] is True; assert r['temporal_admitted_window_count']==1
def test_report_review_contracts_time(tmp_path):
 write_payload(tmp_path/'event_window_builder_lite_v1.json',[base_window()],False); r=build_report(tmp_path,root=ROOT); assert r['time_admission_status']=='REVIEW_REQUIRED'; assert r['downstream_time_allowed'] is False; assert r['routed_windows_sample'][0]['routing_decision']=='UPSTREAM_TIME_REVIEW_REQUIRED'; assert r['routed_windows_sample'][0]['temporal_admission'] is False
def test_claim_locks(tmp_path):
 write_payload(tmp_path/'event_window_builder_lite_v1.json',[base_window()],True); r=build_report(tmp_path,root=ROOT); assert r['canonical_event_count']=='UNKNOWN'; assert r['true_action_count']=='UNKNOWN'; assert r['production_release'] is False
def test_flat_outputs(tmp_path):
 write_payload(tmp_path/'event_window_builder_lite_v1.json',[base_window()],True); out=tmp_path/'HPFA'; out.mkdir(); r=write_outputs(tmp_path,out,root=ROOT); assert (out/'time_scale_router_lite_v1.json').exists(); assert r['claim_safety']=='TIME_SCALE_CANDIDATE_ONLY'
def test_no_sample_match_identity_leak():
 src=(SRC/'time_scale_router.py').read_text();
 for token in ['Turkey','Australia','Türkiye','Avustralya','World Cup','13.06.2026']: assert token not in src
