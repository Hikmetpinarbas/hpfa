# HPFA Termux Integrity Tree Deep Donor Scan V1

NODE: hpfa_termux_integrity_tree_deep_donor_scan_v1
STATUS: READ_ONLY_SCAN_COMPLETE

## Runtime Evidence

OUTPUT: /data/data/com.termux/files/home/storage/downloads/HPFA_NOW/hpfa_termux_integrity_tree_deep_donor_scan_v1.tsv
LINE_COUNT: 14664
BYTE_SIZE: 2349755
SHA256: b11b8879c24b33c328efa84c9f76d2e21cbe5123e005c7211433f2817942c994

## Axis Counts

- A02_THEORY_FORMULA: 8410
- OTHER: 1952
- A08_REGISTRY_RELEASE: 1308
- A05_PHASE_SEQUENCE: 1098
- A07_CLAIM_SAFETY: 1016
- A04_DATA_QUALITY_AUTHORITY: 509
- A06_METRIC_PRIMITIVE: 316
- A03_ONTOLOGY_SCHEMA: 54

## Risk Counts

- RISK_REVIEW: 7912
- OK: 6751

## Portable Counts

- NO: 13922
- YES_REVIEW: 741

## Product Owner Translation

The active HPFA tree contains a very large training library and donor archive. It is rich, but most of it is not ready to enter the first-team product package.

The strongest material is theory/formula and registry/release evidence. The portable candidate pool is smaller: 741 files require review for possible portable core use.

## Key Product Implication

The next action is not broad document generation. The next action is cutting 741 review candidates into a small set of composite candidates.

## Correct Build Direction

1. canonical ingest candidate cut
2. data quality gate candidate cut
3. phase sequence candidate cut
4. claim gate candidate cut
5. metric primitive candidate cut
6. registry audit candidate cut
7. portable package candidate cut

## Guardrails

- No RISK_REVIEW item is promoted.
- No archive, delete-gate, match001, sample or reference material is used as runtime authority.
- No Google Drive or Dropbox source is required at runtime.
- No registry write.
- No production binding.
- No Sprint 2.

## Decision

READ_ONLY_SCAN_ACCEPTED

## Next Node

hpfa_portable_core_candidate_cutline_v1
