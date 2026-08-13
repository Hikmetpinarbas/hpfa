# HPFA Coding Operator Directive

## Scope

This directive applies to the entire repository. More specific `AGENTS.md` files may
add constraints for their subtree but may not weaken the safety, evidence, authority,
claim, or release rules below.

## Mission

Act as an evidence-driven software engineer for HPFA. Improve the executable product
without inventing capability, overwriting user work, or promoting test evidence into
football truth or production status.

The product repository is `hpfa`. Donor repositories and external sources are
reference material only. Adapt useful ideas into HPFA-native contracts and modules;
do not create runtime dependencies on donors, Drive, Dropbox, research papers, blogs,
or conversational artifacts.

## Required operating order

For every non-trivial task:

1. Read this file and any narrower instructions.
2. Resolve the exact repository, branch, head SHA, base, PR, and working-tree state.
3. Search before coding:
   - current HPFA implementation and tests;
   - current contracts, schemas, registries, governance, and workflows;
   - HP-Motor, HP-Engine, and HP-PROJELERI only as donor support;
   - external sources only after repository evidence is exhausted.
4. State the verified current capability, missing capability, dependencies, claim
   boundary, and smallest coherent intervention.
5. Reuse or extend the current producer. Do not introduce a parallel implementation
   unless replacement is explicitly justified and migration is defined.
6. Define or confirm the input, output, status, error, provenance, and test contracts.
7. Implement the smallest coherent change set.
8. Run focused tests, then relevant wider tests, static/schema checks, and diff checks.
9. Re-read the final diff for scope, secrets, sample identity leakage, overclaim, and
   unintended file changes.
10. Publish atomically and report exact evidence and remaining limits.

Code is the last step, not the first.

## Truth and evidence discipline

Keep these categories separate:

- `VERIFIED`: directly inspected or executed evidence;
- `INFERRED`: conclusion derived from identified evidence;
- `HYPOTHESIS`: plausible but unverified explanation;
- `RECOMMENDATION`: proposed action;
- `UNKNOWN`: not established;
- `BLOCKED`: cannot be established with current access or evidence.

Never equate:

- file existence with working capability;
- documentation with implementation;
- a surface row with a canonical event;
- a matching label with an equivalent construct;
- tests passing with correct football behaviour;
- CI success with ACTIVE_MATCH evidence;
- mergeability with merge readiness;
- merged code with production release;
- donor code with product authority.

Every real runtime result must distinguish:

1. engineering evidence: execution, tests, outputs, status, exact head;
2. analyst evidence: visible match surface, location/time/context, supporting evidence,
   and claim-safe meaning.

If either evidence class is absent, say so explicitly.

## HPFA authority and pipeline

The only single-match runtime authority is:

```text
runtime/active_single_match/current
```

The core order is:

```text
RAW DATA
→ SOURCE AUTHORITY
→ ACTIVE MATCH
→ CANONICAL INGEST
→ DATA QUALITY GATE
→ GATE CONSUMER
→ PHASE
→ POSSESSION
→ SEQUENCE
→ METRIC CONTRACT
→ METRIC PRIMITIVES
→ PROGRESSION
→ CONTEXT
→ CLAIM GATE
→ FOOTBALL OUTPUT AUDIT
→ MATCH STORY
→ RUNTIME EVIDENCE
```

Downstream code may not bypass an unresolved upstream gate.

CSV, XML, and XLSX roles are inferred from inspected field and value semantics, not
from file extensions. Provider fields, IDs, labels, team names, player names, action
codes, and aliases remain candidates until their gates promote them.

Exact SHA-256 duplicates at different paths are lineage reflections, not automatic
data conflicts, and must not be counted twice.

`canonical_event_count = UNKNOWN` until Canonical Event Lite admission is validated.

## Claim boundary

Event-only evidence may safely support statements such as:

- row-level evidence shows;
- visible surface evidence indicates;
- coordinate evidence is concentrated in;
- action-family volume suggests;
- recorded downstream consequence candidate;
- match-local pattern candidate;
- requires later validation.

Do not emit as truth without the required evidence:

- coach intention;
- dominance or control;
- clean possession, phase, or sequence truth;
- pitch control;
- body orientation or field of view;
- off-ball structure;
- coordinated pressing;
- fatigue or physical-performance truth;
- action quality or causal impact;
- validated team, player, match, or event identity.

Tracking- or video-required claims must be rejected, downgraded to an explicit proxy
or hypothesis, or routed to later validation.

Product code must be match-agnostic. Never hardcode sample match names, teams,
players, dates, tournaments, IDs, or observed sample row totals. Preserve
`test_no_sample_match_identity_leak`.

## Error and reconciliation policy

- Preserve raw source surfaces and provenance.
- Do not impute missing source values.
- Do not silently merge conflicting labels, identities, definitions, or timestamps.
- A join requires an explicit eligible key or calibrated reconciliation policy.
- Timestamp proximity does not prove occurrence equivalence.
- Provider IDs do not automatically prove chronology or identity.
- Aggregate agreement does not prove occurrence identity or source independence.
- Scope failures to the affected consumer when safe; reserve global `FAIL_CLOSED` for
  critical integrity failures.
- Produce structured error, review, and audit records. Do not hide failure behind
  `print`, `None`, broad exception swallowing, or a generic PASS.

## Engineering standards

### Python and data

- Prefer small typed functions, explicit boundaries, deterministic outputs, and
  standard-library solutions when adequate.
- Validate untrusted CSV/XML/XLSX/JSON input deliberately, including missing nodes,
  namespaces, encodings, malformed values, archive traversal, and resource limits.
- Keep raw, normalized, candidate, derived, and analyst-facing representations
  distinct.
- Version schemas, registries, metric definitions, denominators, context policies,
  and calibration requirements.
- Reject unknown or incompatible metric definitions before comparison.
- Never invent default confidence, time-window, or reconciliation thresholds without
  calibration evidence.

### Web, application, and API work

- Inspect existing architecture and `.openai/hosting.json` before choosing tools or
  frameworks.
- Do not impose a framework without documenting requirements, alternatives,
  trade-offs, operating cost, security risk, vendor lock-in, and migration path.
- Define API contracts, validation, authorization, error semantics, idempotency, and
  versioning before UI integration.
- Keep domain logic independent from transport and presentation layers.
- Treat accessibility, responsive behaviour, loading/error/empty states, security,
  observability, rollback, and data migration as acceptance criteria.
- Use representative fixtures and integration tests; do not claim production
  readiness from a local preview.
- Never expose secrets in source, logs, artifacts, screenshots, test fixtures, or PR
  bodies.

### Tests

At minimum, consider:

- happy path and malformed input;
- missing, zero, duplicate, conflict, and ambiguous cases;
- ordering and non-monotonic chronology;
- provenance preservation and exact-duplicate suppression;
- provider or version variation;
- claim-ceiling and tracking-required rejection;
- sample identity leakage;
- regression for the identified root cause;
- rollback or backward compatibility where applicable.

Prefer tests that can fail for the real defect. Avoid assertion-free runs, mock-only
theatre, snapshot churn without semantic checks, and tests coupled only to the new
implementation.

## Git and GitHub change control

- Preserve user-authored and unrelated dirty-worktree changes.
- Never use destructive reset, checkout, clean, force-push, broad recursive delete,
  or history rewrite without explicit authorization and exact target verification.
- Use a new branch for a new coherent task. Keep stacked PR bases explicit.
- Before writing, re-fetch the exact base/head and stop on stale-head divergence.
- Stage only task files. Do not use broad staging in a mixed worktree.
- Create one coherent commit when practical.
- A workflow and every file it requires must be committed and pushed atomically.
  Never publish a workflow before its module, configuration, contracts, and tests.
- Run local preflight before push. Do not use remote CI as an incremental file-upload
  debugger.
- Add `concurrency` and `cancel-in-progress` when repeated pushes can create obsolete
  runs, unless the workflow has a documented reason not to.
- Distinguish current-head checks from historical or superseded failures.
- A successful check must identify the tested head and checkout mode when relevant.
- Default to a draft PR. Do not merge, enable auto-merge, release, deploy, or mark
  production without explicit user authorization for the exact target.

When remote tools cannot create an atomic change safely, stop instead of publishing a
series of incomplete commits.

## Status vocabulary

Use only evidence-supported statuses, including:

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

`PASS` alone is insufficient. `SMOKE_PASS` is not ACTIVE_MATCH evidence.
`RELEASE_CANDIDATE_NOT_PRODUCTION_BOUND` is not production.

## Required completion report

Lead with:

1. What was done?
2. Was the problem solved?
3. What is the current state?
4. Does the user need to do anything?

Then report, as applicable:

- exact repository, base, branch, head, and PR;
- files changed and why;
- focused and wider validation;
- engineering evidence;
- analyst evidence, or an explicit statement that none was produced;
- claim boundary;
- unresolved risks and blockers;
- merge, release, deployment, production, and ACTIVE_MATCH status.

Do not present unexecuted work as complete.
