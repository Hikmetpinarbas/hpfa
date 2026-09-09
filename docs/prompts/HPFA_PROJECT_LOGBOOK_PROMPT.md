# HPFA PROJECT LOGBOOK PROMPT — SHORT

Use this prompt at the end of every HPFA work session.

Produce a project logbook entry in Turkish.

HPFA = Hikmet Pınarbaş Football Analytics.

HPFA is a ZFGV/EFOD-based, claim-safe, modular and portable Football Intelligence Platform. Event/action evidence is one observation family inside ZFGV, not the whole observation universe.

Your job is to maintain product continuity, not only summarize the conversation.

## Canonical Observation Rule

Never use global `event-only compatible?` as a product gate.

For every construct ask:

- which observation capabilities are required?
- which are actually available/admitted?
- what source/evidence strength do they have?
- what is the safe claim ceiling?
- what must be downgraded/abstained/externally verified?

Canonical rule:

`required_capabilities ⊆ admitted_capabilities`

Observation families:

- ACTION / EVENT
- ENTITY / ACTOR
- TEMPORAL
- SPATIAL
- OUTCOME / QUALIFIER
- RELATIONAL
- PROCESS / PARTICIPATION
- AGGREGATE / TABULAR
- EXTERNAL CONTEXT
- TRACKING / VIDEO — only when actually present
- HPFA-DERIVED INTELLIGENCE

Legacy `event-only` identifiers may remain for compatibility/history. Classify them as GLOBAL_ERROR / LEGITIMATE_EVENT_TERM / LEGACY_IDENTIFIER / HISTORICAL before changing them.

## Required Structure

# HPFA Project Logbook Entry — YYYY-MM-DD

## Session Summary

Write:

- date
- session title
- active branch if known
- Termux working directory if used
- main product node
- secondary research node if any

## Source Authority

Classify every source used as one of:

- GITHUB_PRODUCT_REPO
- GITHUB_DONOR_REPO
- DRIVE_GOVERNANCE
- DRIVE_DONOR_LIBRARY
- DROPBOX_ARCHIVE
- DROPBOX_DONOR_LIBRARY
- ACADEMIC_RESEARCH_SUPPORT
- TERMUX_RUNTIME_EVIDENCE
- ACTIVE_MATCH_RUNTIME_AUTHORITY

State clearly:

- what was runtime evidence
- what was donor support
- what was governance support
- what was academic support
- what must not be treated as match truth

Mandatory rule:

Only `runtime/active_single_match/current` can be runtime match truth.

## Engineering Evidence

Record every engineering action.

Include:

- command/action executed
- file created
- file updated
- test run
- PASS / FAIL / BLOCKED status
- output path when applicable
- whether GitHub write happened
- whether ACTIVE_MATCH execution happened

PASS means only what the test proves.

Do not convert PLAN_ONLY or SPEC_ONLY into release status.

## Analyst Evidence

Record what the football analyst gained.

Answer:

- What became clearer?
- What new observation capability became usable?
- Which evidence block was produced?
- Which analyst-facing output improved?
- Which football reading became safer or more useful?
- What is still forbidden because the required observation capability is absent?

Main text should focus on defensible football meaning. Limits belong in Claim Boundary or technical limits, not as repeated analyst prose.

## Claim Boundary

List:

- allowed statements
- blocked statements
- downgraded statements
- abstained statements
- required evidence before promotion

Mandatory guardrails unless separately admitted:

Do not emit as truth:

- dominance
- coach intention
- tactical plan
- true team shape / compactness / defensive-line height
- pitch control
- off-ball geometry / run truth / option geometry
- body orientation / scanning
- true pressure geometry
- true physical speed/load/fatigue
- causality
- canonical event count
- true action count

Provider labels, coordinates, process labels, aggregates, recurrence or model outputs do not by themselves override these locks.

## Product Status

Normalize the session result into one of:

- DISCOVERY_PASS_PLAN_ONLY
- POLICY_CORRECTION_PASS
- SPEC_ONLY
- IMPLEMENTED
- TESTED
- SMOKE_PASS
- PARTIALLY_VALIDATED
- REVIEW_REQUIRED
- FAIL_CLOSED
- RELEASE_CANDIDATE_NOT_PRODUCTION_BOUND
- ACTIVE_MATCH_EVIDENCE_PASS
- PRODUCTION_RELEASE

Explain why.

## Files / Artifacts

For each important file write:

- file path
- role
- status
- runtime authority: yes/no
- product code/contract/governance: which
- GitHub productization needed: yes/no
- event-only migration class if relevant

Historical event-only examples must remain identified as historical or legacy; do not silently rewrite history.

## Open Items

Separate open items into:

### Real gaps

Items that block evidence-spine or professional analyst progress.

### Event-only migration debt

Global gates, prompts, contracts, tests or legacy apparatus that still suppress valid ZFGV capabilities.

### Intentional waits

Valuable items waiting for upstream observations/contracts.

### Research backlog

Ideas not ready for productization.

### GitHub gaps

Branches, PRs, files or modules not yet in main.

## Next Correct Step

Give exactly one next step.

It must close a real evidence-spine or ZFGV capability gap and state the analyst gain.

Do not list ten alternatives.

## Handoff Block

End with a compact handoff block that can be pasted into a new ChatGPT session.

Include:

- current repo state
- current product priority
- source authority rule
- current ZFGV migration state
- active blockers
- next correct product action

## Output Rules

Write in Turkish.

Use direct, operational language.

Do not claim background work.

Do not claim GitHub write unless a GitHub write actually happened.

Do not claim ACTIVE_MATCH validation unless physical ACTIVE_MATCH execution actually happened.

Do not call visible rows canonical events.

Do not treat aggregate/tabular surfaces as action identity or independent evidence votes.

Always distinguish:

- engineering evidence
- analyst evidence
- source authority
- observation capability
- claim boundary
- release status
