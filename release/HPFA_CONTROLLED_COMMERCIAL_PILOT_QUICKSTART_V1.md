# HPFA Controlled Commercial Pilot — Quickstart V1

Status: OWNER_AUTHORIZED_CONTROLLED_COMMERCIAL_PILOT  
Production release: false  
Public package-index upload: not authorized

## What the customer receives

- HPFA-owned software and claim-safety contracts.
- Installation / execution instructions.
- Analyst-facing outputs generated from match packages the customer is authorized to use.
- Release-readiness and acceptance evidence for the exact delivered software head.

Raw provider match data, raw donor/vendor source, historical runtime dumps and secrets are not part of the commercial software bundle.

## Minimum environment

- Python 3.10+
- Local filesystem access
- Match package placed by the operator/customer under:
  `runtime/active_single_match/current`

The base HPFA core declares no mandatory third-party Python runtime dependency. Optional file formats may require optional packages and must degrade rather than silently change football truth when unavailable.

## Run

From the extracted HPFA directory:

```bash
python active_match_spine_runner.py runtime/active_single_match/current \
  --out-dir out/current \
  --full-spine \
  --execution-root .
```

Expected professional delivery surfaces include:

- `HPFA_ANALYST_REPORT_TR.txt`
- `HPFA_ANALYST_REPORT_EN.txt`
- `HPFA_PROFESSIONAL_REPORT.html`
- `HPFA_PRESENTATION_VIEW_MODEL.json`
- `HPFA_FOOTBALL_DELIVERY.zip`
- machine-readable evidence/claim artefacts

## Interpretation rule

A generated report is not allowed to strengthen upstream evidence or claim admission. When no professional claim is admitted, the report must be visibly labelled as analyst-review narrative rather than an admitted professional finding.

`canonical_event_count=UNKNOWN` and `true_action_count=UNKNOWN` remain valid states.

## Commercial scope

This package is suitable only for a controlled, assisted commercial pilot. It is not a public package-index release and is not a claim of production-wide provider portability.

Match-data rights remain with the customer/provider. HPFA software ownership does not create redistribution rights over provider data.
