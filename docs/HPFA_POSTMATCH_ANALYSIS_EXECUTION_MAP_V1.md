# HPFA Postmatch Analysis Execution Map V1

Status: ROADMAP / EXECUTION GOVERNANCE
Date: 2026-06-21
Repository: Hikmetpinarbas/hpfa
Runtime authority: Termux ACTIVE_MATCH only

## 1. Purpose

This document is not a new architecture proposal. It is the controlled match-analysis execution map derived from existing HPFA work: Data Quality Gate V1, Gate Report Consumer V1, Progression Sprint outputs, donor apparatus notes, and Drive / Dropbox / Sider research support.

The map answers one product question:

> Through which controlled stages does a match analysis pass before it may become a professional football output?

## 2. Current status

```txt
DATA_QUALITY_GATE_V1 = MERGED_TO_MAIN + ACTIVE_MATCH_EXECUTION_PASS
GATE_REPORT_CONSUMER_V1 = MERGED_TO_MAIN
CANONICAL_INGEST_ENGINE = PLANNED_NEXT_MODULE
PHASE_SEQUENCE_COMPOSITE = SPEC_ONLY / DONOR_READY
METRIC_CONTRACT_REGISTRY = CANDIDATE_STUB
PROGRESSION_ENGINE = RELEASE_CANDIDATE_NOT_PRODUCTION_BOUND
CLAIM_GATE = NOT_EXECUTABLE
FOOTBALL_OUTPUT_AUDIT = GLOBAL_ENGINE_PENDING
REPORT_LAYER = NOT_PRODUCTION_BOUND
```

Boundary:

```txt
PRODUCT_RELEASE = NO
PRODUCTION_BINDING = NO
REGISTRY_WRITE = NO
CLAIM_LAYER = BLOCKED
```

## 3. Professional football flow

```txt
Is the match source authorized?
↓
Is the active match selected from runtime authority?
↓
Are raw surfaces discovered and classified?
↓
Are vendor formats translated into HPFA canonical event language?
↓
Is the event surface healthy enough for analysis?
↓
Can events be placed into phase / possession / sequence context?
↓
Are requested metrics contractually valid and computable?
↓
Can primitives produce evidence-only numeric signals?
↓
Can progression be contextualized without overstating the data?
↓
Can consequence and context be attached safely?
↓
Can evidence be converted into a safe claim state?
↓
Is output language safe?
↓
Is football output coherent and audit-safe?
↓
Can a runtime evidence pack be released?
```

## 4. Engineering execution flow

```txt
01 SOURCE_AUTHORITY_GATE
↓
02 ACTIVE_MATCH_SELECTION
↓
03 RAW_SURFACE_DISCOVERY
↓
04 CANONICAL_INGEST
↓
05 DATA_QUALITY_GATE
↓
06 GATE_REPORT_CONSUMER
↓
07 PHASE_SEQUENCE_SEGMENTATION
↓
08 METRIC_CONTRACT_REGISTRY_CHECK
↓
09 METRIC_PRIMITIVE_COMPUTATION
↓
10 PROGRESSION_ENGINE
↓
11 CONSEQUENCE_CONTEXT_ATTACHMENT
↓
12 CLAIM_GATE_SAFE_LANGUAGE
↓
13 FOOTBALL_OUTPUT_AUDIT
↓
14 MATCH_STORY_REPORT_LAYER
↓
15 RELEASE_RUNTIME_EVIDENCE_PACK
```

Gate Report Consumer is explicitly included between Data Quality Gate and downstream modules because PR #9 made it a main-branch policy consumer. Downstream modules must not bypass it.

## 5. Stage summary

| stage_id | stage_name | purpose | product_status |
|---|---|---|---|
| 01 | SOURCE_AUTHORITY_GATE | Exclude non-runtime authority sources from the execution chain. | ACTIVE_POLICY |
| 02 | ACTIVE_MATCH_SELECTION | Select the actual match surface from the active runtime folder. | OPERATOR_RUNTIME_STEP |
| 03 | RAW_SURFACE_DISCOVERY | Classify available Teams / Players / Goalkeepers / raw surfaces. | PARTIAL_RUNTIME_POLICY |
| 04 | CANONICAL_INGEST | Translate provider formats into HPFA common event language. | PLAN_ONLY / NEXT_PRODUCT_MODULE |
| 05 | DATA_QUALITY_GATE | Validate structural quality of the event surface. | EXECUTION_PROVEN_CORE_COMPONENT |
| 06 | GATE_REPORT_CONSUMER | Convert gate_report status into downstream permission. | MERGED_TO_MAIN |
| 07 | PHASE_SEQUENCE_SEGMENTATION | Build phase / possession / sequence evidence. | SPEC_ONLY / DONOR_READY |
| 08 | METRIC_CONTRACT_REGISTRY_CHECK | Check metric contracts and required columns. | CANDIDATE_STUB |
| 09 | METRIC_PRIMITIVE_COMPUTATION | Compute evidence-only numeric signals. | NOT_YET_EXECUTABLE_IN_CORE_SPINE |
| 10 | PROGRESSION_ENGINE | Produce progression evidence with required context. | RELEASE_CANDIDATE_NOT_PRODUCTION_BOUND |
| 11 | CONSEQUENCE_CONTEXT_ATTACHMENT | Attach score, phase, zone, sequence and outcome context. | OPEN_RISK |
| 12 | CLAIM_GATE_SAFE_LANGUAGE | Decide claim state and rewrite unsafe wording. | NEEDS_EXECUTABLE_ADAPTATION |
| 13 | FOOTBALL_OUTPUT_AUDIT | Verify output coherence and claim safety. | GLOBAL_ENGINE_PENDING |
| 14 | MATCH_STORY_REPORT_LAYER | Build professional story/report only after audit. | BINDING_PENDING |
| 15 | RELEASE_RUNTIME_EVIDENCE_PACK | Write output, hash, status and release decision pack. | STANDARD_PACK_REQUIRED |

## 6. Stage policy template

Every stage must be specified with the following fields:

```txt
stage_id
stage_name
purpose
input
output
responsible_repo_or_source
candidate_files
required_gate
claim_boundary
failure_mode
next_if_pass
next_if_degraded
next_if_fail_closed
product_status
```

The complete machine-readable stage map is stored in:

```txt
docs/hpfa_postmatch_analysis_stage_map_v1.tsv
```

The dependency graph is stored in:

```txt
docs/hpfa_postmatch_analysis_dependency_graph_v1.tsv
```

## 7. Donor promotion rule

External repositories and libraries are donor sources, not runtime authority.

```txt
HP-Motor / HP-Engine / HP-PROJELERI = donor / apparatus source
Google Drive = governance + documentation + donor library
Dropbox = research / donor / archive
Sider Scholar = academic donor discovery
GitHub hpfa = canonical code shelf
Termux ACTIVE_MATCH = runtime proof authority
```

No donor code is copied as-is. Donor behavior is adapted into HPFA modules under HPFA contracts.

## 8. Critical dependency rule

The following chain must not be bypassed:

```txt
Data Quality Gate
→ Gate Report Consumer
→ Phase / Sequence Evidence
→ Metric Contract Registry Check
→ Metric Primitive Computation
→ Claim Gate / Safe Language
→ Football Output Audit
```

Progression Engine must remain release-candidate, not production-bound, until these are available:

```txt
DATA_QUALITY_GATE_PASS
PHASE_SEQUENCE_EVIDENCE_OUTPUT
CLAIM_GATE_SAFE_LANGUAGE_POLICY
```

## 9. Final decision

```txt
HPFA_POSTMATCH_ANALYSIS_EXECUTION_MAP_V1 = ACTIVE_ROADMAP_NODE
NEW_ARCHITECTURE = NO
EXISTING_SPINE_ORDERING = YES
NEXT_ENGINEERING_MODULE = CANONICAL_INGEST_ENGINE
PROGRESSION_BINDING = HOLD
CLAIM_LAYER = BLOCKED
PRODUCT_RELEASE = NO
```
