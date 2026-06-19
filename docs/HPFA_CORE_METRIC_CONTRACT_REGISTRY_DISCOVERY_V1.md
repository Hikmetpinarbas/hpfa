# HPFA Core Metric Contract Registry Discovery V1

NODE: hpfa_core_metric_contract_registry_discovery_v1
STATUS: DISCOVERY_PASS_PLAN_ONLY

Purpose: define the first coding-oriented core spine target after portable candidate cutline.

Product meaning: before HPFA uses a metric in a match report, it must know the metric role, required columns, calculation rule, degraded state and confidence.

Primary donor:

HP-Motor/hp_motor/library/registry/metric_registry.json

Observed donor fields:

- id
- layer
- mechanisms
- definition
- raw_formula
- required_columns
- status_policy
- definition_confidence

Observed metric examples:

- M_PASS_COUNT
- M_PROG_PASS_COUNT
- M_SHOT_COUNT
- M_TURNOVER_COUNT
- M_SEQUENCE_LENGTH

Target path:

hpfa/modules/core/metric_contract_registry/

Planned files:

- contracts/metric_contract_schema_v1.json
- src/metric_registry_loader.py
- src/metric_required_column_gate.py
- src/metric_status_policy_evaluator.py
- src/metric_definition_confidence_audit.py
- tests/test_metric_contract_registry_active_match.py

Product rule:

Metric primitive library must not become production-bound until metric contracts can answer required columns, calculation rule, status state and evidence capacity.

Current decision:

DISCOVERY_PASS_PLAN_ONLY

Next node:

hpfa_core_metric_contract_registry_schema_spec_v1
