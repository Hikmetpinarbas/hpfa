# HPFA Coding Operator Directive — Current

## Scope

This directive applies repository-wide. Narrower `AGENTS.md` files may add constraints but may not weaken authority, evidence, claim-safety, runtime, release, or provenance rules here.

## Product authority

- Executable product authority: `Hikmetpinarbas/hpfa`.
- Single ACTIVE_MATCH runtime authority: `runtime/active_single_match/current`.
- Drive, Dropbox, donor repositories, PDFs, academic sources, old chats, historical PRs, CI artifacts, and prior runtime bundles are not current product truth.
- External material may be classified only as `DONOR_SUPPORT`, `RESEARCH_SUPPORT`, `REFERENCE_ONLY`, or `HISTORICAL_LINEAGE` unless current HPFA explicitly admits it.

## Donor law

- `ADAPT_NOT_COPY`.
- `REHABILITATE_BEFORE_PARALLEL_ENGINE`.
- `CODE_LAST`.
- Search current HPFA producers/contracts/tests before proposing a new node.
- If a capability already exists, strengthen the current producer instead of creating a parallel implementation.
- Donor code, donor release state, donor PASS status, and donor runtime truth never transplant into product truth.

## Required operating order

For non-trivial work:

1. Resolve current repository, `main` head, target branch/head, PR/issue state, checks, and review threads.
2. Identify the real product gap and the current producer responsible for it.
3. Follow source order: current HPFA → HP-Motor → HP-Engine → HP-PROJELERI → Drive → Dropbox → academic/web → targeted runtime/Termux discovery → code.
4. Define the contract, admission rule, prerequisites, invariants, provenance, dependency model, claim ceiling, failure behavior, and tests.
5. Reuse or rehabilitate the existing producer where possible.
6. Implement the smallest coherent change.
7. Run focused regression, relevant wider tests, exact-head CI, static/schema guards, and sample-identity-leak protection.
8. Separate engineering evidence from analyst evidence.
9. Re-read the final diff for authority drift, duplicate evidence, chronology overclaim, sample hardcoding, claim promotion, secrets, and unintended files.
10. Publish only coherent, reviewable changes. Do not represent unexecuted work as complete.

## Product evidence spine

Use this as the conceptual direction, not as a claim that every node currently exists:

```text
RAW / SURFACE
→ SOURCE AUTHORITY
→ ACTIVE MATCH
→ READERS / SEMANTICS
→ REFLECTION CONTROL
→ ROW NUCLEUS
→ EVIDENCE ATOM
→ MATCH-LOCAL IDENTITY
→ ACTION CANDIDATE
→ PARTIAL ORDER
→ CONSEQUENCE
→ CONTEXT
→ EPISODE
→ FEATURES
→ CHANGE
→ RECURRENCE / VARIATION / DEVIATION
→ COUNTEREVIDENCE
→ METRIC / MODEL
→ DEFEASIBLE FINDING
→ ANALYST REPORT
```

Upstream admission controls downstream truth. Never skip a missing prerequisite because a later metric or report would be useful.

## Default claim locks

Unless an explicit current gate proves otherwise:

```text
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
phase_truth=false
possession_truth=false
sequence_truth=false
tactical_truth=false
production_release=false
```

`PASS != RELEASE`.
`SMOKE_PASS != ACTIVE_MATCH`.
`CI SUCCESS != ACTIVE_MATCH`.
`MERGED != PRODUCTION_RELEASE`.
Runtime evidence is not production release.

## Evidence, identity, and dependency rules

- CSV/XML/XLSX row count is not canonical event count.
- `ROW_NUCLEUS != ACTION_OCCURRENCE`.
- `ACTION_BUNDLE != CANONICAL_EVENT`.
- Provider labels, team/player fields, action fields, IDs, aliases, and coordinates are candidates until admitted by explicit gates.
- Same SHA at different paths is a reflection/lineage duplicate, not independent evidence.
- CSV/XML reflections of the same upstream observation are not independent corroboration.
- N metrics do not imply N independent evidence units.
- Derived evidence should preserve, where applicable: `provenance_root`, `derivation_parents`, `dependency_group`, and `independence_group`.
- Repeated canonical evidence identity may not multiply independent support.
- Conflicting lineage for one evidence identity must fail closed or remain review-bounded; it must never inflate confidence.

## Time and order

Numeric parseability is not football chronology.

Admission of temporal meaning requires semantic role, unit, clock basis, period/context, and provenance.

Never infer chronology from source row order, list order, event index, or same timestamp.
Use explicit relations such as:

```text
BEFORE_CONFIRMED
AFTER_CONFIRMED
SAME_TIME_UNORDERED
ORDER_INDETERMINATE
PROVENANCE_ORDER_ONLY
```

Same timestamp must not create an internal total order unless stronger evidence exists.

## Event-only claim ceiling

Event-only evidence does not directly prove:

- pitch control;
- team shape;
- defensive-line height;
- compactness;
- off-ball structure or run;
- passing-option geometry;
- body orientation or scanning;
- fatigue, load, or physical speed truth;
- true pressure geometry;
- coach intention;
- tactical plan;
- dominance;
- causality.

If useful, route such outputs as `PROXY_CANDIDATE`, `HYPOTHESIS_ONLY`, `REQUIRES_TRACKING`, or `REQUIRES_VIDEO`.

Absence of observed evidence is not automatically counterevidence.
Recurrence is not coach intention.
Probability is not fact.
Pass networks are not team shape.
PPDA is not pressing truth.
Average position is not formation truth.

## Match-agnostic product rule

Product code must not hardcode sample match, team, player, date, competition, sample ID, or observed sample row count.
Preserve the mandatory regression:

```text
test_no_sample_match_identity_leak
```

## Runtime evidence

Every real run must keep two evidence classes distinct.

Engineering evidence should identify at least:

- exact code head;
- module/input surface;
- test/run evidence;
- output location/artifact;
- status or failure.

Analyst evidence should identify at least:

```text
WHAT_VISIBLE
WHERE_WHEN
SUPPORT
COUNTEREVIDENCE
SAFE_MEANING
FORBIDDEN_INFERENCE
ANALYST_ACTION
```

CI green alone never satisfies ACTIVE_MATCH evidence.

## Football Intelligence direction

The minimum analyst bridge is:

```text
Evidence → Episode → Safe Finding → Analyst Report Block
```

A finding should preserve, where available:

- support;
- counterevidence;
- alternative explanation;
- claim ceiling;
- uncertainty;
- withdrawal condition.

Prefer evidence independence, counterevidence/falsification, episode structure, change/rhythm, recurrence/variation/deviation, spatial/progression primitives, sequence grammar, and cross-match profiling before simply multiplying metric count.

## Metric and model admission

A formula alone is not product capability.

Each metric/model must define its construct, observation surface, inputs/units, eligibility, prerequisites, reference corpus, leakage controls, calibration/validation, null or comparison model where relevant, sensitivity, uncertainty, provenance/dependency, interpretation, claim ceiling, and release state.

xT/xPass/VAEP-like or probabilistic outputs are not production truth without coordinate integrity, direction normalization, eligibility, corpus/version, and validation.

## Red-team checks

Every important change should explicitly challenge:

- correlation → causation;
- row order → chronology;
- same timestamp → total order;
- numeric field → semantic truth;
- metric count → independent evidence;
- pass network → team shape;
- PPDA → pressing truth;
- average position → formation truth;
- probability → fact;
- recurrence → coach intention;
- absence → counterevidence;
- donor PASS → product PASS.

## Git and GitHub control

- Re-fetch current `main`, target head, checks, and reviews before current-state claims or writes.
- Do not force-push, rewrite history, destructive-reset, clean unrelated work, or delete evidence lineage without explicit authorization.
- Do not treat mergeability as merge readiness.
- Keep new coherent tasks on explicit branches/PRs.
- Do not publish partial multi-file runtime changes when atomic publication is required.
- Exact-head validation must be rerun after the PR head moves.
- ACTIVE_MATCH must be rerun only when the accepted scope requires runtime evidence.
- Merge, release, deployment, production binding, repository settings/ruleset mutation, and destructive cleanup require explicit authorization for the exact target.

## Status vocabulary

Use evidence-supported states such as:

```text
DISCOVERY_PASS_PLAN_ONLY
POLICY_CORRECTION_PASS
SPEC_ONLY
SPEC_CORRECTION_ACCEPTED
SMOKE_PASS
REVIEW_REQUIRED
FAIL_CLOSED
WAITING_OPERATOR_SELECTION
RELEASE_CANDIDATE_NOT_PRODUCTION_BOUND
ACTIVE_MATCH_EVIDENCE_PASS
PRODUCTION_RELEASE
```

Do not collapse distinct states into a generic PASS.

## Completion report

Lead with:

1. Ne yapıldı?
2. Sorun çözüldü mü?
3. Current durum?
4. Kullanıcıdan gereken?

Then, only when useful, include exact repository/base/head/PR, changed surfaces, validation evidence, analyst evidence, claim boundary, remaining blockers, and merge/release/ACTIVE_MATCH status.

Final check for every new task:

> Mevcut evidence spine'ın hangi gerçek boşluğunu kapatıyor ve analiste hangi yeni savunulabilir bilgiyi kazandırıyor?

If there is no clear answer, classify the idea as `IDEA_POOL_ONLY`, `LATER`, or `REJECT` instead of adding product code.
