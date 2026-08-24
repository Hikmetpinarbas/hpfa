import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
SRC=ROOT/'hpfa/modules/core/minimum_viable_context_lite/src'; sys.path.insert(0,str(SRC))
from minimum_viable_context import build_report, build_context_candidates, minute_bucket, write_outputs

def test_semicolon_csv_context_extraction(tmp_path):
    (tmp_path/'surface.csv').write_text('minute;team;action;pos_x;pos_y\n10;A;Pass;80;50\n')
    report=build_report(tmp_path,root=ROOT); sample=report['context_candidates_sample'][0]
    assert sample['action_family']=='PASS'; assert sample['zone_candidate']=='FINAL_THIRD'; assert sample['time_admission_status']=='ADMITTED'; assert sample['minute_bucket']=='10'

def test_explicit_second_field_converts_without_magnitude_guess():
    c=build_context_candidates([{'second':'995','team':'A','action':'Pass'}])[0]
    assert c['time_admission_status']=='ADMITTED'; assert c['minute_bucket']=='16'; assert c['time_unit_status']=='SECOND'

def test_ambiguous_numeric_start_is_not_minute_truth():
    c=build_context_candidates([{'start':'995','half':'1','team':'A','action':'Pass'}])[0]
    assert c['minute_bucket']=='unknown'; assert c['time_admission_status']=='REVIEW_REQUIRED_UNKNOWN_TIME_UNIT'; assert c['rejected_time_field_candidates'][0]['reason']=='UNKNOWN_TIME_UNIT'

def test_ambiguous_clock_shape_can_be_admitted():
    c=build_context_candidates([{'timestamp':'12:30','team':'A','action':'Pass'}])[0]
    assert c['time_admission_status']=='ADMITTED'; assert c['minute_bucket']=='12'; assert c['time_unit_status']=='CLOCK'

def test_no_magnitude_heuristic_helper():
    assert minute_bucket(1001) == 'unknown'; assert minute_bucket(1001,'SECOND')=='16'

def test_previous_next_are_never_synthetic_source_adjacency():
    sample=build_context_candidates([{'minute':10,'action':'Pass'},{'minute':11,'action':'Shot'}])
    assert all(x['previous_action_family']=='UNKNOWN_PREVIOUS_ACTION' for x in sample)
    assert all(x['next_action_family']=='UNKNOWN_NEXT_ACTION' for x in sample)
    assert all(x['synthetic_previous_next_adjacency_allowed'] is False for x in sample)

def test_claim_boundaries_remain_false(tmp_path):
    (tmp_path/'surface.csv').write_text('minute,team,action,x,y\n10,A,Pass,50,34\n')
    report=build_report(tmp_path,root=ROOT)
    assert report['canonical_event_count']=='UNKNOWN'; assert report['true_action_count']=='UNKNOWN'; assert report['phase_truth'] is False; assert report['sequence_truth'] is False; assert report['production_release'] is False

def test_flat_outputs(tmp_path):
    (tmp_path/'surface.csv').write_text('minute,team,action,x,y\n10,A,Pass,50,34\n'); out=tmp_path/'HPFA'; out.mkdir(); report=write_outputs(tmp_path,out,root=ROOT)
    assert (out/'minimum_viable_context_lite_v1.json').exists(); assert report['claim_safety']=='CONTEXT_CANDIDATE_ONLY'

def test_no_sample_match_identity_leak():
    src=(SRC/'minimum_viable_context.py').read_text()
    for token in ['Turkey','Australia','Türkiye','Avustralya','World Cup','13.06.2026']: assert token not in src
