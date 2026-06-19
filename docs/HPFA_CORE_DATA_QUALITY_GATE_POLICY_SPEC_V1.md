# HPFA Core Data Quality Gate Policy Spec V1

NODE: hpfa_core_data_quality_gate_policy_spec_v1
STATUS: SPEC_PLAN_ONLY

## Purpose

Specify the future generic HPFA data quality gate policy.

## Football Product Meaning

This is the medical and equipment check before the team walks onto the pitch.

If the match file fails this check, HPFA must not produce confident football observations.

## Future Policy Target

hpfa/modules/core/data_quality_gate_engine/policies/data_quality_gate_policy_v1.yaml

## Future Implementation Target

hpfa/modules/core/data_quality_gate_engine/

Planned parts:

- schema gate
- duplicate gate
- coordinate gate
- temporal gate
- team identity gate
- anomaly rate gate
- period gate
- authority source gate
- reference exclusion gate
- degraded mode gate

## Policy Requirements

1. Generic policy only.
2. No fixed team names.
3. No fixed match001 assumptions.
4. No PDF event truth.
5. No archive or sample authority.
6. Every fail or degraded result must produce an audit reason.

## PASS Meaning

The event surface can be used by phase, sequence, metric and claim layers.

## DEGRADED Meaning

The event surface can be used only with warning and limited output.

## FAIL_CLOSED Meaning

The event surface cannot be used for product analysis.

## Current Decision

SPEC_PLAN_ONLY

## Next Node

hpfa_postmatch_phase_sequence_donor_discovery_v1
