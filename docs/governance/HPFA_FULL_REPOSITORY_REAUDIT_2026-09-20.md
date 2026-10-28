# HPFA FULL REPOSITORY RE-AUDIT — 2026-09-20

Status: LIVING AUDIT / CURRENT PR #364 SUPPORT WORK / NOT RELEASE AUTHORITY

## 1. Executive result

The current HPFA product core is materially healthier than the repository surface suggests.

Verified on the audited #364 line:
- 72 / 72 current core modules have test coverage.
- full product pytest: 1898 passed, 0 failed, 0 errors.
- YelFootballLab donor repo: 185 passed, 0 failed.
- no credential pattern hit in the current repository scan.
- current ACTIVE_MATCH exact-head run completed REVIEW_REQUIRED with 0 professional EMIT and production_release=false.
- Turkish and English analyst-facing reports now exist separately from the technical audit report.

The largest remaining risks are no longer basic test failure. They are:
1. release/history convergence between the current ZFGV stack and main;
2. stale governance/backlog surfaces that can misdirect a future operator;
3. professional report composition still below the target match-story level;
4. incomplete robustness/context-conditioned comparison capital;
5. repository hygiene / packaging / legacy surface ambiguity.

## 2. Repository inventory snapshot

{
  "tracked_files": 1381,
  "core_files": 450,
  "support_files": 10,
  "postmatch_files": 15,
  "reporting_files": 4,
  "docs_files": 234,
  "vendor_files": 201,
  "legacy_hpfa_main_files": 36,
  "out_files": 82,
  "runtime_evidence_files": 3,
  "root_python_files": 63
}

Interpretation:
- repository size is inflated by tracked outputs, legacy/imported trees, vendor donor code and historical data.
- file count is not capability count.
- hpfa-main and vendor remain non-current authority.
- root entry wrappers must be classified by reachability before deletion; duplicate basename alone is not a defect.

## 3. Closed during this re-audit

### 3.1 Portable Termux test debt — CLOSED
The aggregate-alignment runner is Git 100755 but Termux materializes it as owner-executable 0700.
The old test incorrectly required group/other execute bits.
The regression now checks the actual portability contract: current user execution.

### 3.2 Untested core module — CLOSED
xlsx_entity_metric_row_projection_lite had no dedicated tests.
Added fail-closed, truth-lock, identity/metric projection and inventory/audit mismatch coverage.
Current audit therefore reaches 72/72 core modules with tests.

### 3.3 Bilingual analyst report gap — PARTIALLY CLOSED / CONTINUING
Added:
- HPFA_ANALYST_REPORT_TR.txt
- HPFA_ANALYST_REPORT_EN.txt

The analyst layer now renders:
- visible team process profile;
- player/pair × attack-outcome review candidates;
- mechanism candidates;
- separate evidence notes and claim boundaries.

Internal tokens such as LAYER[...] and raw epistemic field names are not intended to dominate the analyst-facing sentence.

### 3.4 C02 governance bridge — CLOSED FOR CURRENT SCOPE
C02 match-local descriptive association now reaches governed composition without:
- creating independent support;
- converting missing target annotation into counterevidence;
- causal player credit;
- statistical-significance truth;
- strengthening the MATCH_LOCAL_VISIBLE_ASSOCIATION_ONLY ceiling.

## 4. Current product gaps

### 4.1 Safe Finding → professional Match Story — CURRENT_PRODUCT_GAP / HIGH
The system now finds process families, contrast variants, consequence differences, counterevidence and analyst-attention candidates.
The remaining product problem is composition:
- 3–5 real football mechanisms;
- successful / failed / deviant variants;
- opponent response;
- consequence;
- counterevidence;
- safe meaning;
- why the analyst should care;
- trace-back;
- compression / information gain / truth loss.

0 EMIT remains valid when evidence does not clear the contract.

### 4.2 Context-conditioned trace deviation — CURRENT_PRODUCT_GAP / LATER IN CURRENT SEQUENCE
Current tree has admitted context components and process-comparison context contracts.
It does not yet demonstrate a complete general context-conditioned trace-distribution product matching old issue #349.
Do not open it ahead of the current Safe Finding composition bottleneck.

### 4.3 Recurrence robustness envelope — CURRENT_PRODUCT_GAP / ADAPT_LATER
Current recurrence/variant capital is strong, but a complete robustness envelope is not closed.
A current source still reports threshold_sensitivity_state=NOT_TESTED_V1.
Old issue #347 therefore should not be treated as fully implemented.

### 4.4 Player/process association — CURRENT_SCOPE COMPLETE, INFERENCE NOT REQUIRED
Current C02 is descriptive and match-local.
Do not add Fisher/permutation/bootstrap/shrinkage by default.
Formal inference is RESEARCH_REQUIRED only after observation-unit, denominator, dependency and exchangeability contracts justify it.

## 5. Open issue / backlog triage

Do not auto-close from this audit.

- #340 Partial-Order Trace Variant: IMPLEMENTED_CLOSE_CANDIDATE. Current partial_order_occurrence_variant_projection preserves SAME_TIME_UNORDERED.
- #343 Trace Similarity Primitive: IMPLEMENTED_CLOSE_CANDIDATE / SEMANTICALLY ABSORBED. Current dependency_aware_partial_order_similarity_projection includes multiset Jaccard and comparison eligibility.
- #345 Success/Failure Twin Trace Comparator: IMPLEMENTED_CLOSE_CANDIDATE / SEMANTICALLY ABSORBED by observable process variants, supported divergence and comparable-outcome counterevidence.
- #347 Recurrence Robustness Envelope: STILL_OPEN_REAL_GAP / PARTIAL.
- #349 Context-Conditioned Trace Deviation: STILL_OPEN_REAL_GAP / PARTIAL.
- #351 Object-Centric Trace Binding: REVIEW_REQUIRED. Occurrence→trace binding exists, but the exact object-centric relation vocabulary from the issue is not fully demonstrated in the current audit.
- #361 Legacy Intelligence Mine: KEEP OPEN AS LEDGER, not as parallel WIP.
- older EVENT-ONLY-framed issues: HUMAN TRIAGE REQUIRED; current ZFGV tree may supersede their ontology even when useful sub-capabilities remain.

## 6. Release / history debt

Classification: RELEASE_CONVERGENCE_DEBT / HIGH / NOT A RUNTIME BUG.

Observed:
- current #364 line is built over #359;
- #359 history does not form a simple natural ancestry chain back through the expected older release/main line;
- many older PR heads are DISCONNECTED_HISTORY or DIVERGED_SHARED_HISTORY relative to the current head;
- origin/main and current product tree therefore cannot be treated as a trivial merge-ready lineage.

Forbidden response:
- no force-push;
- no reset/revert;
- no blind rebase;
- no blind merge/cherry-pick.

Required future action:
build an explicit convergence plan from tree/content truth, then ask for user release authority before merging.

## 7. Governance/documentation debt

### Stale current handoff — FIXED IN THIS AUDIT
HPFA_OPERATOR_HANDOFF_CURRENT.md still named #359 and an old ZFGV migration audit as current WIP.
It is being updated to #364 + Safe Football Finding Composition.

### Open PR / issue count ≠ current backlog truth
Old PR/issue bodies must be interpreted as historical/support surfaces unless current tree/runtime proves they are current gaps.

## 8. Repository hygiene

Classification: HYGIENE_ONLY unless reachability proves otherwise.

Observed:
- vendor tracked files: 201
- nested hpfa-main tracked files: 36
- tracked out files: 82
- tracked runtime_evidence files: 3
- multiple root Python entry wrappers share basenames with canonical core implementations.

No mass deletion is authorized.
First classify each surface as CURRENT_RUNTIME_REACHABLE / CI_ONLY / LEGACY_ONLY / DONOR_ONLY / DEAD_CODE_CANDIDATE.

The apparent hpfa-main remote mutation in run_active_match_multiformat_inventory_v1.sh was inspected and is a NEGATIVE SELF-TEST, not a current-authority bug.

## 9. Packaging / dependency debt

Classification: TECHNICAL_DEBT / NON-BLOCKING FOR CURRENT ACTIVE_MATCH.

pyproject.toml is not a faithful representation of the modern hpfa/modules/core product tree.
requirements.txt is also not the authoritative dependency manifest.
Current XLSX runtime uses a native OOXML reader; openpyxl is mostly a test/bootstrap fixture dependency, while optional xlrd/PDF readers have their own optional paths.

Do not “fix” packaging by blindly adding every CI-installed package to runtime dependencies.
A separate packaging contract should be built only when distribution/installability becomes a product need.

## 10. YelFootballLab donor assessment

Fresh donor checkout: 185 tests PASS.

Useful donor capital:
- finding → natural football narrative → limitation structure;
- comparison-design/outcome-leakage discipline;
- counterevidence / withdrawal framing;
- math capability mapping as research guidance.

Adapted now:
- only the presentation idea of turning governed findings into natural football language while keeping evidence limits separate.
- no Yel engine copied.

Rejected for blind transplant:
- fixed thresholds as evidence truth;
- Event-Only assumptions where ZFGV is broader;
- any donor inference that bypasses current HPFA identity/dependency/censoring contracts;
- any parallel finding/match-story engine.

## 11. Security / portability

Credential-pattern scan: no hit in the audited current tree.
Product-specific sample names found in historical/data/test/output surfaces are not automatically runtime hardcoding.
Current code must remain match-agnostic; future sample-literal findings must be classified by current-runtime reachability before action.

## 12. Current priority

WIP remains one:

MECHANISM CANDIDATE
→ SAFE FOOTBALL FINDING COMPOSITION
→ PROFESSIONAL TURKISH / ENGLISH ANALYST OUTPUT
→ MATCH STORY

Repository cleanup, Yel donor work and research are subordinate to this path.

## 13. Release locks

canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false

No merge / ready-for-review / release / production binding without explicit user authority.
