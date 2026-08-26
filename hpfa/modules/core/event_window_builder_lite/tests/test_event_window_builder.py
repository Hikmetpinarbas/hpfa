import json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[5]
SRC=ROOT/'hpfa/modules/core/event_window_builder_lite/src'
sys.path.insert(0,str(SRC))

from event_window_builder import build_report,build_windows_from_context,write_outputs


def c(m,a='PASS',team='a'):
    return {'minute_bucket':str(m),'football_minute_candidate':m,'time_admission_status':'ADMITTED','action_family':a,'team_label':team,'period':'1H','zone_candidate':'MIDDLE_THIRD','channel_candidate':'CENTRAL_CHANNEL'}


def write_context(path,contexts):
    path.write_text(json.dumps({'module_id':'minimum_viable_context_lite_v1','context_candidate_count':len(contexts),'context_candidates_sample':contexts}))


def test_builds_windows_from_minimum_context_json(tmp_path):
    rows=[c(1),c(4,'SHOT'),c(6,'RECOVERY','b')]
    write_context(tmp_path/'minimum_viable_context_lite_v1.json',rows)
    r=build_report(tmp_path,root=ROOT,window_size_mins=5,hop_mins=5)
    assert r['event_window_count']==2


def test_window_counts_actions():
    w=build_windows_from_context([c(0),c(1),c(2,'SHOT')])[0]
    assert w['action_family_counts']=={'PASS':2,'SHOT':1}
    assert w['surface_row_count']==3


def test_terminal_flags():
    w=build_windows_from_context([c(0,'SHOT'),c(1,'BALL_LOSS'),c(2,'RESTART','b')])[0]
    assert w['terminal_action_surface_present']
    assert w['loss_recovery_surface_present']
    assert w['restart_surface_present']


def test_raw_input_rebuilds_explicit_minute(tmp_path):
    out=tmp_path/'HPFA'
    out.mkdir()
    raw=tmp_path/'raw'
    raw.mkdir()
    write_context(out/'minimum_viable_context_lite_v1.json',[{'minute_bucket':'unknown','action_family':'UNKNOWN_OR_OTHER','team_label':'unknown'}])
    (raw/'surface.csv').write_text('minute_raw;team;action;pos_x;pos_y\n5;A;Pass;50;34\n6;A;Shot;80;44\n')
    r=build_report(out,root=ROOT,raw_input_dir=raw)
    assert r['minute_bearing_context_count']==2
    assert r['event_window_count']==1


def test_raw_ambiguous_start_fails_closed(tmp_path):
    raw=tmp_path/'raw'
    raw.mkdir()
    (raw/'surface.csv').write_text('start;half;team;action\n995;1;A;Pass\n1000;1;A;Shot\n')
    r=build_report(raw,root=ROOT,raw_input_dir=raw)
    assert r['minute_bearing_context_count']==0
    assert r['time_admission_status']=='REVIEW_REQUIRED'
    assert r['minute_window_enabled'] is False


def test_event_window_never_claims_canonical_action_identity(tmp_path):
    rows=[c(0)]
    write_context(tmp_path/'minimum_viable_context_lite_v1.json',rows)
    r=build_report(tmp_path,root=ROOT)
    assert r['canonical_action_id_present'] is False
    assert r['canonical_action_identity_status']=='UNKNOWN'
    assert r['canonical_action_identity_basis']=='NO_ADMITTED_STABLE_ACTION_ID'
    assert r['canonical_event_count']=='UNKNOWN'


def test_flat_outputs(tmp_path):
    rows=[c(0)]
    write_context(tmp_path/'minimum_viable_context_lite_v1.json',rows)
    out=tmp_path/'HPFA'
    out.mkdir()
    r=write_outputs(tmp_path,out,root=ROOT)
    assert (out/'event_window_builder_lite_v1.json').exists()
    assert r['claim_safety']=='EVENT_WINDOW_CANDIDATE_ONLY'


def test_no_sample_match_identity_leak():
    src=(SRC/'event_window_builder.py').read_text()
    for token in ['Turkey','Australia','Türkiye','Avustralya','World Cup','13.06.2026']:
        assert token not in src
