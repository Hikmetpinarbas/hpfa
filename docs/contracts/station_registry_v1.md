# Station Registry V1

Status: CONTRACT CANDIDATE.

A metric using "station" is invalid unless station_type and registry version are explicit.

## Registry fields
station_type_id, name, definition, identity_key, new_station_rule, same_station_rule, eligible_observation_families, required_fields, optional_fields, deduplication_rule, ordering_requirement, count_unit, forbidden_inferences, claim_ceiling.

## ST01 ACTOR_STATION
Distinct admitted actor participation point. Re-entry policy must be declared. Not touch count. Does not prove role or intention.

## ST02 ACTION_STATION
One admitted occurrence nucleus. Reflected provider labels collapse before count.

## ST03 RELATION_STATION
One admitted relation nucleus, e.g. passer→receiver or action→visible opponent response.

## ST04 ZONE_STATION
One admitted canonical zone state. Grid/zone registry version mandatory. Same-zone actions do not automatically create new stations.

## ST05 PROCESS_STAGE_STATION
One admitted semantic process-stage candidate. Semantic stage order does not create factual action order.

## ST06 HYBRID_STATION
Declared tuple such as actor-role candidate + action family + zone + process stage. Research/similarity use only; sparsity and missingness must be exposed.

## Hard rules
- Same timestamp never creates total order.
- Station counts are typed and non-fungible.
- Different station types cannot be added into one generic station count without an explicit construct.
- Tracking-level station meaning is forbidden without tracking.

production_release=false
