#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any, Dict, List

try:
    from .chain_segmenter import segment_chains
    from .io_utils import read_events, write_json, write_jsonl
    from .phase_tagger import tag_phases
    from .sequence_segmenter import split_sequences
except ImportError:
    from chain_segmenter import segment_chains
    from io_utils import read_events, write_json, write_jsonl
    from phase_tagger import tag_phases
    from sequence_segmenter import split_sequences


def _load_gate(path: str | None) -> Dict[str, Any] | None:
    if not path:
        return None
    import json
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _gate_allows(report: Dict[str, Any] | None, degraded_mode: bool) -> bool:
    if report is None:
        return True
    try:
        from hpfa.modules.core.data_quality_gate.src.downstream_policy import is_downstream_allowed
        return bool(is_downstream_allowed(report, 'phase_sequence', degraded_mode=degraded_mode))
    except Exception:
        status = str(report.get('status', '')).upper()
        if status == 'PASS':
            return True
        if status == 'DEGRADED':
            return degraded_mode
        return False


def _phase_rows(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for event in events:
        rows.append({
            'event_index': event.get('event_index'),
            'event_id': event.get('event_id') or event.get('ID') or event.get('id') or '',
            'team_id': event.get('team_id') or event.get('team') or '',
            'period': event.get('period') or event.get('half') or '',
            'time_seconds': event.get('time_seconds') or event.get('t_game_sec') or event.get('start') or '',
            'event_type': event.get('event_type') or event.get('action') or event.get('type') or event.get('code') or '',
            'phase_id': event.get('phase_id'),
            'phase_confidence': event.get('phase_confidence'),
            'evidence_tags': event.get('phase_evidence_tags', []),
            'degraded_flags': event.get('phase_degraded_flags', []),
            'claim_safety': 'EVIDENCE_ONLY'
        })
    return rows


def run(input_path: str, out_dir: str, gate_report: str | None = None, degraded_mode: bool = False) -> Dict[str, Any]:
    report = _load_gate(gate_report)
    if not _gate_allows(report, degraded_mode):
        summary = {
            'status': 'FAIL_CLOSED',
            'reason': 'upstream_gate_blocks_phase_sequence',
            'events_in': 0,
            'phase_events_out': 0,
            'possessions_out': 0,
            'sequences_out': 0,
            'degraded': False,
            'claim_safety': 'EVIDENCE_ONLY',
            'next_action': {'metric_layer_allowed': False, 'report_language_allowed': False}
        }
        write_json(str(Path(out_dir) / 'phase_sequence_summary.json'), summary)
        return summary

    events = read_events(input_path)
    tagged = tag_phases(events)
    chains = segment_chains(tagged)
    sequences = split_sequences(tagged, chains)
    out = Path(out_dir)
    write_jsonl(str(out / 'phase_events.jsonl'), _phase_rows(tagged))
    write_jsonl(str(out / 'possessions.jsonl'), chains)
    write_jsonl(str(out / 'sequences.jsonl'), sequences)
    degraded = any(row.get('phase_degraded_flags') for row in tagged) or any(c.get('flags') for c in chains)
    summary = {
        'status': 'DEGRADED' if degraded else 'PASS',
        'events_in': len(events),
        'phase_events_out': len(tagged),
        'possessions_out': len(chains),
        'sequences_out': len(sequences),
        'degraded': bool(degraded),
        'claim_safety': 'EVIDENCE_ONLY',
        'next_action': {'metric_layer_allowed': True, 'report_language_allowed': False},
        'sequence_type_counts': {},
    }
    for seq in sequences:
        key = seq.get('sequence_type', 'unknown')
        summary['sequence_type_counts'][key] = summary['sequence_type_counts'].get(key, 0) + 1
    write_json(str(out / 'phase_sequence_summary.json'), summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--out-dir', required=True)
    parser.add_argument('--gate-report', default=None)
    parser.add_argument('--degraded-mode', action='store_true')
    args = parser.parse_args()
    summary = run(args.input, args.out_dir, gate_report=args.gate_report, degraded_mode=args.degraded_mode)
    print(summary)


if __name__ == '__main__':
    main()
