import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]; SRC=ROOT/'hpfa/modules/core/event_window_builder_lite/src'; sys.path.insert(0,str(SRC))
from sequence_output_contract_guard import build_sequence_output_contract

def base_report():
 return {'claim_safety':'EVENT_WINDOW_CANDIDATE_ONLY','time_axis_status':'AVAILABLE','time_admission_status':'ADMITTED','ordering_status':'VISIBLE_TIME_AVAILABLE','ordering_authority':'PARTIAL_ORDER_ONLY','window_integrity_summary':{'downstream_ready':True},'event_window_count':1,'canonical_action_id_present':True,'event_windows_sample':[{'window_id':'w','window_axis':'minute','temporal_admission':True,'time_semantic_admission':True,'source_row_order_is_temporal_truth':False,'same_timestamp_internal_ordering_allowed':False,'team_label_counts':{'a':2},'action_family_counts':{'PASS':1,'SHOT':1},'claim_boundary':'event_window_candidate_only'}]}
def test_ready_with_explicit_admission():
 c=build_sequence_output_contract(base_report()); assert c['hard_block_hits']==[]; assert c['sequence_decision']=='READY_FOR_SEQUENCE_CANDIDATE_CONSUMER'
def test_review_report_blocks_timestamp_order():
 r=base_report(); r['time_admission_status']='REVIEW_REQUIRED'; c=build_sequence_output_contract(r); assert 'timestamp_or_order_missing' in c['hard_block_hits']
def test_context_ordinal_never_counts():
 r=base_report(); w=r['event_windows_sample'][0]; w['window_axis']='context_ordinal'; w['temporal_admission']=False; w['time_semantic_admission']=False; assert build_sequence_output_contract(r)['required_fields_present']['timestamp_or_order'] is False
def test_claim_locks():
 c=build_sequence_output_contract(base_report()); assert c['sequence_truth'] is False; assert c['canonical_event_count']=='UNKNOWN'; assert c['production_release'] is False
