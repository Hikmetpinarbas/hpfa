from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / 'hpfa' / 'modules' / 'postmatch' / 'phase_sequence_composite' / 'src'
sys.path.insert(0, str(SRC))

from phase_tagger import tag_phases
from chain_segmenter import segment_chains
from sequence_segmenter import split_sequences
from phase_sequence_runner import run
from sequence_features import build_features


def sample_events():
    return [
        {'event_id': '1', 'team_id': 'A', 'event_type': 'pass', 'minute': 1, 'second': 0, 'start_x': 20, 'end_x': 34, 'x': 20, 'y': 30},
        {'event_id': '2', 'team_id': 'A', 'event_type': 'carry', 'minute': 1, 'second': 5, 'start_x': 34, 'end_x': 55, 'x': 34, 'y': 30},
        {'event_id': '3', 'team_id': 'A', 'event_type': 'shot', 'minute': 1, 'second': 12, 'start_x': 86, 'end_x': 88, 'x': 86, 'y': 32},
        {'event_id': '4', 'team_id': 'B', 'event_type': 'recovery', 'minute': 1, 'second': 20, 'start_x': 40, 'end_x': 50, 'x': 40, 'y': 30},
        {'event_id': '5', 'team_id': 'B', 'event_type': 'pass', 'minute': 1, 'second': 25, 'start_x': 50, 'end_x': 62, 'x': 50, 'y': 30},
    ]


def test_phase_tags_are_evidence_only():
    tagged = tag_phases(sample_events())
    assert len(tagged) == 5
    assert all(row['claim_safety'] == 'EVIDENCE_ONLY' for row in tagged)
    assert any(row['phase_id'] == 'P3_FINALIZATION' for row in tagged)


def test_chain_fallback_and_sequence_features():
    tagged = tag_phases(sample_events())
    chains = segment_chains(tagged)
    sequences = split_sequences(tagged, chains)
    assert chains
    assert chains[0]['possession_authority'] == 'FALLBACK_TEAM_RUN'
    assert sequences
    assert all(seq['claim_safety'] == 'EVIDENCE_ONLY' for seq in sequences)
    assert any(seq['shots'] >= 1 for seq in sequences)


def test_runner_writes_outputs(tmp_path):
    inp = tmp_path / 'events.csv'
    inp.write_text('event_id,team_id,event_type,minute,second,start_x,end_x,x,y\n1,A,pass,1,0,20,34,20,30\n2,A,shot,1,5,86,88,86,32\n', encoding='utf-8')
    out = tmp_path / 'out'
    summary = run(str(inp), str(out))
    assert summary['events_in'] == 2
    assert (out / 'phase_events.jsonl').exists()
    assert (out / 'possessions.jsonl').exists()
    assert (out / 'sequences.jsonl').exists()
    assert (out / 'phase_sequence_summary.json').exists()
    assert summary['claim_safety'] == 'EVIDENCE_ONLY'


def test_explicit_possession_id_is_used():
    events = sample_events()
    for i, row in enumerate(events):
        row['possession_id'] = 'P1' if i < 3 else 'P2'
    tagged = tag_phases(events)
    chains = segment_chains(tagged)
    assert len(chains) == 2
    assert chains[0]['possession_id'] == 'P1'
    assert chains[0]['possession_authority'] == 'EXPLICIT_POSSESSION_ID'


def test_output_contract_fields_present():
    tagged = tag_phases(sample_events())
    chains = segment_chains(tagged)
    sequences = split_sequences(tagged, chains)
    assert 'possession_id' in chains[0]
    assert 'possession_authority' in chains[0]
    assert 'degraded_flags' in chains[0]
    assert 'claim_safety' in chains[0]
    assert 'possession_id' in sequences[0]
    assert 'claim_safety' in sequences[0]
    assert 'degraded_flags' in sequences[0]


def test_provider_action_taxonomy_counts_features():
    rows = [
        {'event_type': 'Passes accurate', 'team_id': 'A', 'start_x': 20, 'pos_x': 20, 'start': 1},
        {'event_type': 'Progressive passes accurate', 'team_id': 'A', 'start_x': 40, 'pos_x': 40, 'start': 3},
        {'event_type': 'Shots on target', 'team_id': 'A', 'start_x': 86, 'pos_x': 86, 'start': 8},
        {'event_type': 'Ball recoveries', 'team_id': 'A', 'start_x': 60, 'pos_x': 60, 'start': 10},
        {'event_type': 'Lost balls', 'team_id': 'A', 'start_x': 55, 'pos_x': 55, 'start': 12},
    ]
    features = build_features(rows, 'S1', 'P1', 'unit')
    assert features['passes'] == 2
    assert features['shots'] == 1
    assert features['recoveries'] == 1
    assert features['sequence_type'] != 'recycle_or_build_sequence'
    assert features['claim_safety'] == 'EVIDENCE_ONLY'

def test_runner_active_match_requires_gate_report(tmp_path):
    inp = tmp_path / 'events.csv'
    inp.write_text(
        'event_id,team_id,event_type,minute,second,start_x,end_x,x,y\n'
        '1,A,pass,1,0,20,34,20,30\n',
        encoding='utf-8'
    )
    out = tmp_path / 'out_gate_required'
    summary = run(str(inp), str(out), require_gate_report=True)
    assert summary['status'] == 'FAIL_CLOSED'
    assert summary['reason'] == 'missing_required_gate_report'
    assert summary['next_action']['metric_layer_allowed'] is False


def test_half_boundary_splits_chain_and_sequence():
    rows = [
        {'event_id': '1', 'team_id': 'A', 'event_type': 'pass', 'half': 1, 'period': 1, 'start': 2690, 'start_x': 20, 'end_x': 30, 'coordinate_scale': '105x68'},
        {'event_id': '2', 'team_id': 'A', 'event_type': 'pass', 'half': 2, 'period': 2, 'start': 2705, 'start_x': 30, 'end_x': 40, 'coordinate_scale': '105x68'},
    ]
    tagged = tag_phases(rows)
    chains = segment_chains(tagged)
    sequences = split_sequences(tagged, chains)
    assert len(chains) == 2
    assert any(c['boundary_reason'] == 'half_change' for c in chains)
    assert all(seq['coordinate_scale'] == '105x68' for seq in sequences)


def test_sequence_features_carry_context_metadata():
    rows = [
        {'event_type': 'Passes accurate', 'team_id': 'A', 'start_x': 20, 'pos_x': 20, 'start': 1, 'half': 1, 'period_scope': 'first_half', 'score_state': '0-0', 'coordinate_scale': '105x68'},
        {'event_type': 'Shots on target', 'team_id': 'A', 'start_x': 86, 'pos_x': 86, 'start': 8, 'half': 1, 'period_scope': 'first_half', 'score_state': '0-0', 'coordinate_scale': '105x68'},
    ]
    result = build_features(rows, 'S_CTX', 'P_CTX', 'unit')
    assert result['coordinate_scale'] == '105x68'
    assert result['surface_row_count'] == 2
    assert result['half'] == 1
    assert result['period_scope'] == 'first_half'
    assert result['score_state'] == '0-0'

