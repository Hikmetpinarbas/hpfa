import json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[5]
SRC=ROOT/'hpfa/modules/core/axis_integrity_tagger_lite/src'
sys.path.insert(0,str(SRC))

from axis_integrity_tagger import AVAILABLE,MISSING,build_axis_report,write_outputs


def dump(p,d):
    p.write_text(json.dumps(d))


def seed(p,admitted=True,with_second=True,raw_second_only=False):
    dump(p/'time_scale_router_lite_v1.json',{
        'routed_window_count':2,
        'minute_axis_window_count':2,
        'event_index_window_count':0,
        'time_admission_status':'ADMITTED' if admitted else 'REVIEW_REQUIRED',
        'downstream_time_allowed':admitted,
    })
    dump(p/'event_window_builder_lite_v1.json',{
        'time_admission_status':'ADMITTED' if admitted else 'REVIEW_REQUIRED',
        'time_axis_status':'AVAILABLE' if admitted else 'MISSING',
        'ordering_status':'VISIBLE_TIME_AVAILABLE' if admitted else 'ORDER_INDETERMINATE',
        'event_windows_sample':[{
            'window_axis':'minute',
            'zone_counts':{'MIDDLE_THIRD':3},
            'team_label_counts':{'A':4},
            'action_family_counts':{'PASS':5},
        }],
    })
    row={'zone_candidate':'MIDDLE_THIRD','team_label':'A','action_family':'PASS','time_admission_status':'ADMITTED' if admitted else 'REVIEW_REQUIRED'}
    if with_second:
        row['admitted_time_evidence']=[{'field':'absolute_time_seconds','raw_value':995,'unit':'SECOND','minute_bucket':16,'basis':'EXPLICIT_ABSOLUTE_SECOND_FIELD'}]
    elif raw_second_only:
        row['second']=34
        row['admitted_time_evidence']=[]
    dump(p/'minimum_viable_context_lite_v1.json',{'context_candidates_sample':[row]})


def test_admitted_minute_axis_available(tmp_path):
    seed(tmp_path,True)
    r=build_axis_report(tmp_path)
    assert r['axis_status']['minute_axis_status']==AVAILABLE
    assert r['downstream_permissions']['downstream_time_allowed'] is True


def test_second_axis_comes_from_admitted_time_evidence(tmp_path):
    seed(tmp_path,True,with_second=True)
    r=build_axis_report(tmp_path)
    assert r['axis_status']['second_axis_status']==AVAILABLE
    assert r['input_counts']['admitted_second_evidence_row_count']==1
    assert r['second_axis_admission_basis']=='ADMITTED_TIME_EVIDENCE_ONLY'
    assert r['raw_second_key_presence_is_axis_authority'] is False


def test_raw_second_key_without_admission_does_not_create_second_axis(tmp_path):
    seed(tmp_path,True,with_second=False,raw_second_only=True)
    r=build_axis_report(tmp_path)
    assert r['axis_status']['second_axis_status']==MISSING
    assert 'admitted_second_axis_evidence_missing' in r['permission_contraction_reasons']


def test_review_time_contracts_all_time_permissions(tmp_path):
    seed(tmp_path,False)
    r=build_axis_report(tmp_path)
    assert r['axis_status']['minute_axis_status']==MISSING
    assert r['axis_status']['second_axis_status']==MISSING
    assert r['downstream_permissions']['downstream_time_allowed'] is False
    assert r['downstream_permissions']['downstream_phase_candidate_allowed'] is False
    assert r['downstream_permissions']['downstream_sequence_candidate_allowed'] is False
    assert r['downstream_permissions']['downstream_rhythm_candidate_allowed'] is False
    assert 'upstream_time_semantics_not_admitted' in r['permission_contraction_reasons']


def test_space_team_action_still_descriptive(tmp_path):
    seed(tmp_path,False)
    r=build_axis_report(tmp_path)
    assert r['axis_status']['space_axis_status']==AVAILABLE
    assert r['axis_status']['team_axis_status']==AVAILABLE
    assert r['axis_status']['action_family_axis_status']==AVAILABLE


def test_claim_locks(tmp_path):
    seed(tmp_path,True)
    r=build_axis_report(tmp_path)
    assert r['canonical_event_count']=='UNKNOWN'
    assert r['true_action_count']=='UNKNOWN'
    assert r['sequence_truth'] is False
    assert r['production_release'] is False


def test_flat_outputs(tmp_path):
    seed(tmp_path,True)
    out=tmp_path/'HPFA'
    out.mkdir()
    r=write_outputs(tmp_path,out,root=ROOT)
    assert (out/'axis_integrity_tagger_lite_v1.json').exists()
    assert r['claim_safety']=='AXIS_INTEGRITY_CANDIDATE_ONLY'


def test_no_sample_match_identity_leak():
    assert 'sample_match_identity_token' not in (SRC/'axis_integrity_tagger.py').read_text()
