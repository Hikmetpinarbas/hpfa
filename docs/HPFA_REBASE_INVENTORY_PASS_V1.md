# HPFA Rebase Inventory PASS V1

NODE: hpfa_clean_canonical_rebase_inventory_v1
STATUS: PASS

OUTPUTS

- hpfa_clean_canonical_rebase_inventory_v1.tsv
- hpfa_clean_canonical_rebase_inventory_v1_summary.txt
- hpfa_operator_handover_current.md
- handover/current_operator_handover.md

EVIDENCE

- line_count: 19714
- byte_size: 5955205
- sha256: d7b1253170808a4d12b148fdb4f3e679157ac761ff44739b309619ca2ca596e5

ACTION SUMMARY

- REVIEW: 11272
- QUARANTINE: 3458
- MERGE_TO_COMPOSITE: 2594
- BIND_TO_CORE: 968
- DONOR_ONLY: 809
- REFERENCE_ONLY: 612

PRIORITY SUMMARY

- P0: 968
- P1: 5920
- P2: 4007
- P3: 6734
- P4: 602
- P5: 1482

POSTMATCH RELEVANCE SUMMARY

- CRITICAL: 1078
- HIGH: 5810
- MEDIUM: 4007
- LOW: 2114
- REVIEW: 6704

ROLE SUMMARY

- canonical_code_candidate: 7761
- runtime_script: 2825
- registry_document: 1916
- archive_only: 1502
- reference_only: 1171
- donor_only: 847
- apparatus_candidate: 416
- execution_proven_runtime: 226
- unknown_review: 3049

DECISION

Proceed to hpfa_clean_postmatch_spine_design_v1 only after reviewing P0 and P1 inventory rows.

NEXT NODE

hpfa_clean_postmatch_spine_design_v1

GUARDRAIL

This was an inventory node only. No delete, move, rewrite, registry write, or production binding was performed.
