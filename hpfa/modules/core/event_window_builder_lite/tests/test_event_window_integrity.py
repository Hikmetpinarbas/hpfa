import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]; SRC=ROOT/'hpfa/modules/core/event_window_builder_lite/src'; sys.path.insert(0,str(SRC))
from event_window_builder import build_report,build_windows_from_context,duplicate_time_flags,ordering_status,same_time_multiplicity_summary,temporal_gap_flags

def ctx(minute=None,**kw):
    d={'action_family':'PASS','team_label':'a','period':'1H','time_admission_status':'ADMITTED' if minute is not None else 'MISSING','football_minute_candidate':minute,'minute_bucket':str(minute) if minute is not None else 'unknown','zone_candidate':'MIDDLE_THIRD','channel_candidate':'CENTRAL_CHANNEL'}; d.update(kw); return d
def write_context(path,contexts,reported=None): path.write_text(json.dumps({'module_id':'minimum_viable_context_lite_v1','context_candidate_count':reported if reported is not None else len(contexts),'context_candidates_sample':contexts}))
def test_missing_time_order_indeterminate(): assert ordering_status([ctx(None)])=='ORDER_INDETERMINATE'
def test_complete_visible_minute_is_available_even_shuffled(): assert ordering_status([ctx(7),ctx(1),ctx(4)])=='VISIBLE_TIME_AVAILABLE'
def test_partial_time_review_required(): assert ordering_status([ctx(1),ctx(None)])=='REVIEW_REQUIRED'
def test_provenance_bucket_not_temporal():
    w=build_windows_from_context([ctx(None) for _ in range(105)])[0]; assert w['window_axis']=='context_ordinal'; assert w['temporal_admission'] is False; assert w['source_row_order_is_temporal_truth'] is False
def test_same_minute_rows_no_internal_order():
    w=build_windows_from_context([ctx(1),ctx(1,action_family='SHOT')])[0]; assert w['window_axis']=='minute'; assert w['same_timestamp_internal_ordering_allowed'] is False; assert w['sequence_readiness']['has_ordered_context'] is False
def test_same_minute_multiplicity_not_duplicate():
    rows=[ctx(12) for _ in range(100)]; assert duplicate_time_flags(rows)==[]; m=same_time_multiplicity_summary(rows); assert m['same_time_unordered_bucket_count']==1; assert m['max_surface_rows_in_same_time_bucket']==100
def test_gap_flags_descriptive_not_blocker():
    f=temporal_gap_flags([ctx(20),ctx(1),ctx(2)]); assert f[0]['gap_mins']==18; assert f[0]['admission_blocker'] is False; assert f[0]['sequence_continuity_truth'] is False
def test_shuffled_complete_minute_surface_pass(tmp_path):
    rows=[ctx(8),ctx(2),ctx(5),ctx(3)]; write_context(tmp_path/'minimum_viable_context_lite_v1.json',rows); r=build_report(tmp_path,root=ROOT); assert r['status']=='PASS'; assert r['time_admission_status']=='ADMITTED'; assert r['window_integrity_summary']['downstream_ready'] is True
def test_unknown_unit_context_review(tmp_path):
    rows=[ctx(None,time_admission_status='REVIEW_REQUIRED_UNKNOWN_TIME_UNIT')]; write_context(tmp_path/'minimum_viable_context_lite_v1.json',rows); r=build_report(tmp_path,root=ROOT); assert r['status']=='REVIEW_REQUIRED'; assert r['time_admission_status']=='REVIEW_REQUIRED'; assert r['minute_window_enabled'] is False
def test_truncated_sample_blocks_windows(tmp_path):
    rows=[ctx(1)]; write_context(tmp_path/'minimum_viable_context_lite_v1.json',rows,10); r=build_report(tmp_path,root=ROOT); assert r['event_window_count']==0; assert r['is_truncated_sample'] is True
def test_claim_locks(tmp_path):
    rows=[ctx(1)]; write_context(tmp_path/'minimum_viable_context_lite_v1.json',rows); r=build_report(tmp_path,root=ROOT); assert r['canonical_event_count']=='UNKNOWN'; assert r['true_action_count']=='UNKNOWN'; assert r['production_release'] is False
