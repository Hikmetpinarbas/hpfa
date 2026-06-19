# HPFA Core Data Quality Gate Template Discovery V1

NODE: hpfa_core_data_quality_gate_template_discovery_v1
STATUS: DISCOVERY_PASS_PLAN_ONLY

## Purpose

Define the donor-supported discovery plan for the HPFA data quality gate.

## Football Product Meaning

Data quality gate is the pre-match control room.

It checks whether the match file is healthy enough before phase, sequence, metric, claim or report layers are allowed to speak.

## Source Inputs

- HPFA core donor inventory
- runtime risk inventory
- canonical candidate inventory
- claim candidate inventory
- phase sequence candidate inventory
- metric candidate inventory
- HPFA operator donor-supported productization delivery pack
- HPFA canonical event schema candidate in GitHub

## Required Gate Families

G01 schema gate
G02 duplicate gate
G03 coordinate boundary gate
G04 temporal order gate
G05 team identity gate
G06 anomaly rate gate
G07 period and half gate
G08 authority source gate
G09 reference material exclusion gate
G10 degraded mode gate

## Product Rule

No module can turn event data into football observations until the data quality gate passes or explicitly marks degraded mode.

## Discovery Finding

The donor inventory contains enough candidate material to build the gate family, but many paths include runtime risk, archive, old test, delete-gate or match001 surfaces. These must be treated as donor material only.

## PASS Criteria For This Node

- gate families are identified
- runtime-risk sources are not promoted
- canonical candidates are separated from dirty authority
- no code is moved
- no registry write
- no production binding

## Decision

DISCOVERY_PASS_PLAN_ONLY

## Next Node

hpfa_core_data_quality_gate_policy_spec_v1
