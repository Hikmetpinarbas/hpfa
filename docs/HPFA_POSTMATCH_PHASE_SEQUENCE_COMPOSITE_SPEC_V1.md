# HPFA Postmatch Phase Sequence Composite Spec V1

NODE: hpfa_postmatch_phase_sequence_composite_spec_v1
STATUS: SPEC_PLAN_ONLY

Purpose: specify the future Phase plus Sequence Composite Apparatus.

Football product meaning: this composite tells HPFA where an action sits in the match and what chain it belongs to. It is a context builder, not a final tactical conclusion engine.

Future targets:

- hpfa/modules/postmatch/phase_engine/
- hpfa/modules/postmatch/sequence_engine/
- hpfa/composites/phase_sequence_composite/

Minimum phase output:

- event_id
- match_id
- team_id
- phase_id
- phase_reason
- rule_source
- degraded_flag
- degraded_reason
- claim_safety_status

Minimum sequence output:

- sequence_id
- possession_id if available
- match_id
- team_id
- period
- start_event_id
- end_event_id
- event_count
- duration_sec
- start and end coordinates
- progression distance
- split_reason
- degraded flag and reason

Required upstream gates:

- canonical ingest gate
- data quality gate
- authority source gate
- reference exclusion gate

Current decision:

SPEC_PLAN_ONLY

Next node:

hpfa_core_metric_primitive_donor_discovery_v1
