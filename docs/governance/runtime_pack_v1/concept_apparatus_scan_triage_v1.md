# Concept Apparatus Scan Triage V1

Status: REVIEW_REQUIRED / REFERENCE_ONLY

Linked PR: #92

## Purpose

Record operator-provided Termux concept apparatus scan results and convert them into HPFA product triage without changing current work order.

The scan is useful as discovery evidence, not runtime football truth.

## Input Summary

Operator scan file:

```text
reports/hpfa_concept_apparatus_scan_v1.tsv
```

Observed summary:

```text
TOTAL_MATCHED = 33
```

Top apparatus guesses:

```text
16 APP-SEQUENCE-POSSESSION-CLAIM-CANDIDATE
11 APP-RHYTHM-SPECTROGRAM-CANDIDATE
3 APP-PROGRESSION-THREAT-CANDIDATE
2 CONCEPT_SUPPORT_CANDIDATE
1 APP-GRAPH-NETWORK-CANDIDATE
```

Top source roles:

```text
17 TERMUX_LOCAL_SCAN
8 DROPBOX_ARCHIVE_OR_DONOR
5 GITHUB_DONOR_HP_ENGINE
3 GITHUB_PRODUCT_REPO
```

## Interpretation

The scan confirms that the strongest reusable discovery clusters are:

1. sequence / possession / claim candidate material
2. rhythm / spectrogram candidate material
3. progression / threat candidate material
4. graph / network candidate material

## Product Triage

### Immediate relevance: APP-SEQUENCE-POSSESSION-CLAIM-CANDIDATE

This cluster supports the current product order.

Attach to:

- R1 permission spine closure
- P2C Event-Time-Space Binder
- future sequence candidate builder
- Claim Eligibility Gate
- Football Output Audit

Use now as:

- donor discovery
- candidate vocabulary
- test naming support
- future sequence/claim gate input

Do not use as:

- possession truth
- sequence truth
- tactical truth

### Delayed relevance: APP-RHYTHM-SPECTROGRAM-CANDIDATE

This cluster has high concept score but must not jump ahead of product gates.

Reason:

- Rhythm V12 requires canonical event lite, sequence candidate and signal density gate.
- STFT/spectrogram is optional diagnostic channel, not primary classifier.
- Current P2I work is ontology/style candidate governance, not rhythm production.

Use later as:

- rhythm diagnostic support
- signal-density feature support
- volatility/tempo candidate support

Do not use now as:

- rhythm truth
- match momentum truth
- tactical rhythm claim

### Delayed relevance: APP-PROGRESSION-THREAT-CANDIDATE

Attach later to:

- Metric Readiness Report
- proxy_metric_guard_lite_v1
- Threat / Value Proxy Table
- xT candidate / VAEP-style proxy

Blocked until:

- metric passport
- minimum sample size gate
- proxy label guard
- claim eligibility gate

### Future relevance: APP-GRAPH-NETWORK-CANDIDATE

Attach later to:

- sequence graph candidate
- zone transition matrix
- passing network candidate
- opponent correspondence map

Blocked until:

- Event-Time-Space Binder
- sequence candidate gate
- network source role validation

## Work Order Decision

The scan does not change the current order.

Current order remains:

1. R1 permission spine closure
2. P2C Event-Time-Space Binder
3. P2H Postmatch Report Skeleton
4. P2I Ontology Chain
5. Claim Eligibility Gate
6. Football Output Audit
7. Analyst-facing execution

## Risk Map

Risk 1: Rhythm score dominates and pulls product work too early.

Decision:

Keep rhythm delayed until event-time-space, sequence and signal-density gates exist.

Risk 2: Termux local scan and Dropbox donor files are treated as runtime evidence.

Decision:

All scan outputs remain REFERENCE_ONLY_UNTIL_ACTIVE_MATCH_VALIDATION.

Risk 3: Apparatus candidates become claims.

Decision:

Apparatus guess is only discovery metadata. It cannot produce football interpretation.

## Recommended Next Action

Convert the scan into a repeatable governance input later:

- concept_apparatus_scan_contract_v1
- concept_apparatus_triage_reader_lite_v1
- donor_candidate_to_product_node_router_lite_v1

But do not implement this before R1/P2C closure.

## Status

REVIEW_REQUIRED / REFERENCE_ONLY.

No production release claim.
