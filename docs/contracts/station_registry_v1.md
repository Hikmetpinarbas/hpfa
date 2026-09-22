# Station Registry V1

Status: contract-only.

Purpose: make every "station count" metric typed and reproducible.

Registry entry:
- station_type_id
- name
- definition
- identity_key
- new_station_rule
- same_station_rule
- eligible_observation_families
- required_fields
- optional_fields
- deduplication_rule
- ordering_requirement
- count_unit
- forbidden_inferences
- claim_ceiling

Initial station types:

## ST01 ACTOR_STATION
Identity: admitted actor identity candidate.
Use: actor spread, actor-chain recurrence.
Not equal to touch count.
Cannot prove role or intention.

## ST02 ACTION_STATION
Identity: admitted occurrence nucleus ID.
Reflection labels collapse before count.
One occurrence nucleus remains one station across semantic facets.

## ST03 RELATION_STATION
Identity: admitted relation nucleus.
Examples: passer→receiver; action→visible-opponent-response.

## ST04 ZONE_STATION
Identity: canonical zone ID + zone registry version.
New station only on admitted zone entry/re-entry according to declared rule.

## ST05 PROCESS_STAGE_STATION
Identity: canonical process-stage candidate.
Semantic staging does not create factual action order.

## ST06 HYBRID_STATION
Identity: declared tuple such as (actor-role candidate, action family, zone, process stage).
Research/similarity only by default because sparsity risk is high.

Hard rule:
Any metric named "stations per attack/episode/process" without station_type and registry version is INVALID_METRIC_CONTRACT.
