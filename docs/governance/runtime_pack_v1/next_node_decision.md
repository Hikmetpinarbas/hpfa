# HPFA Next Node Decision V1

Date: 2026-06-22

Status: P0A_GOVERNANCE_FILE

## Decision

The completed evidence-pass nodes are:

```text
P1 ACTIVE_MATCH Analyst Report Lite V1
P2 Canonical Event Lite V1
P2B Reference Document Ingest Lite V1
Fitness Signal PDF Support Lite
Fitness-Tactical Integration Bridge Lite V1
```

The next correct product node is:

```text
P3 Team Binding Lite V1
```

## Reason

P1 created the first analyst-facing surface report.

P2 normalized readable CSV/XML/XLSX surfaces into canonical-lite row evidence and opened coordinate-derived zone/channel evidence.

P2B extracted ACTIVE_MATCH-adjacent reference PDFs into page-level support evidence.

Fitness Signal PDF Support Lite indexed five support PDFs under the ACTIVE_MATCH folder.

Fitness-Tactical Integration Bridge Lite linked event evidence and support-document evidence as non-causal cross-surface review candidates.

## Runtime Evidence Summary

P1 evidence:

```text
py_compile PASS
pytest 4 passed
ACTIVE_MATCH run PASS
canonical_event_count UNKNOWN
flat phone outputs written
```

P2 evidence:

```text
py_compile PASS
pytest 4 passed
ACTIVE_MATCH run PASS
canonical_event_count UNKNOWN
canonical_lite_row_count=15516
coordinate_rows=7713
event_type_rows=7725
team_rows=3680
flat phone outputs written
```

P2B support-document evidence:

```text
pdf_count=5
page_count=141
chars_total=284238
texty_pages=134
err_pages=0
runtime_event_truth=False
flat phone outputs written
```

Bridge evidence:

```text
py_compile PASS
pytest 3 passed
ACTIVE_MATCH flat-output run PASS
candidate_count=2
claim_safety=SUPPORT_BRIDGE_ONLY_NO_CAUSALITY
```

## Analyst Evidence

The analyst now has:

- event-family volume;
- team row-volume;
- coordinate-derived zone/channel distribution;
- PDF support document inventory;
- page-level reference text extraction;
- cross-surface review candidates.

The bridge does not create causal football truth. It creates a review queue for analyst validation.

## Current ACTIVE_MATCH Surface Highlights

```text
canonical_event_count=UNKNOWN
canonical_lite_row_count=15516
PASS=3708
GOALKEEPER_RESTART=1164
DUEL_PRESSURE=748
POSITIONAL_ATTACK_SIGNAL=729
FINAL_THIRD=2794
MIDDLE_THIRD=2758
DEFENSIVE_THIRD=2161
RIGHT_CHANNEL=2960
CENTRAL_CHANNEL=2660
LEFT_CHANNEL=2093
```

## Claim Boundary

Allowed language:

```text
row-level evidence shows
visible surface evidence indicates
support evidence is available beside event evidence
cross-surface review candidate
requires analyst validation
requires claim gate
```

Blocked language families:

```text
causal physical-state claims
coach intention claims
dominance claims
off-ball truth claims
event truth override claims
clean phase or possession truth before gate
```

Required invariants:

```text
canonical_event_count=UNKNOWN
support documents are not runtime event truth
PDF/reference evidence cannot override ACTIVE_MATCH event evidence
```

## Next Executable Step

Write P3 Team Binding Lite V1 contract.

P3 must solve:

- team identifier normalization;
- team label mapping;
- duplicate team surface handling;
- player/team aggregate binding from XLSX;
- event-row team binding from CSV/XML where available;
- no match identity hardcoding;
- no quality claim by identity alone.

Recommended contract path:

```text
docs/contracts/team_binding_lite_v1.md
```

Recommended root output:

```text
/storage/emulated/0/Download/HPFA/team_binding_lite_v1.json
/storage/emulated/0/Download/HPFA/team_binding_lite_audit_v1.txt
```

## Decision Result

```text
P1_ACTIVE_MATCH_EVIDENCE_PASS
P2_ACTIVE_MATCH_EVIDENCE_PASS
P2B_ACTIVE_MATCH_EVIDENCE_PASS
FITNESS_PDF_SUPPORT_ACTIVE_MATCH_EVIDENCE_PASS
FITNESS_TACTICAL_BRIDGE_ACTIVE_MATCH_EVIDENCE_PASS
P3_TEAM_BINDING_LITE_NEXT_PRODUCT_NODE
RHYTHM_IMPLEMENTATION_DEFERRED
PRODUCTION_RELEASE_NOT_GRANTED
```

This file is governance evidence plus operator-reported ACTIVE_MATCH evidence summary. It is not PRODUCTION_RELEASE by itself.
