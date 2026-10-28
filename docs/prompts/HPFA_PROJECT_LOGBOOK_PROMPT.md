# HPFA PROJECT LOGBOOK PROMPT — SHORT

Use this prompt at the end of every HPFA work session.

Produce a project logbook entry in Turkish.

HPFA = Hikmet Pınarbaş Football Analytics.

HPFA is a claim-safe, modular and portable Football Intelligence Platform operating on **Zenginleştirilmiş Futbol Gözlem Verisi (ZFGV)**.

Canonical ontology:

- `EVENT ⊂ ZFGV`
- event is one observation family, not the whole observation universe
- construct admission is capability-specific
- legacy `event_only_compatible` metadata cannot be product admission authority

Your job is to maintain product continuity, not only summarize the conversation.

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
- SIDER_ACADEMIC_BACKING
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

## Observation / Capability Authority

When a session changes admission or eligibility, record:

- observation family/layer
- required observation capabilities
- admitted capabilities
- optional capabilities
- `forbidden_without` prerequisites
- claim ceiling
- whether the construct is ACTION/EVENT-specific or uses another ZFGV family

Do not use a global Event-Only compatibility flag as a product-wide veto.

## Engineering Evidence

Record every engineering action.

Include:

- command executed
- file created
- file updated
- test run
- PASS / FAIL / BLOCKED status
- output path
- whether GitHub write happened
- whether ACTIVE_MATCH execution happened

Use exact language.

PASS means only what the test proves.

Do not convert PLAN_ONLY or SPEC_ONLY into release status.

## Analyst Evidence

Record what the football analyst gained.

Answer:

- What became clearer?
- What can now be seen?
- Which evidence block was produced?
- Which analyst-facing output improved?
- Which football reading became safer or more useful?

Main text should focus on what was visible.

Limits belong in Claim Boundary or technical limits, not as repeated analyst prose.

## Claim Boundary

List:

- allowed statements
- blocked statements
- downgraded statements
- required evidence before promotion

Mandatory guardrails:

Do not emit without the required admitted evidence:

- dominance truth
- coach intention
- off-ball structure truth
- pitch control truth
- body orientation / scanning truth
- fatigue / physical-load truth
- tactical plan truth
- true team shape / compactness / defensive-line height
- canonical event count or true action count
- clean phase truth before the relevant claim/admission gate
- causality from recurrence, provider labels or model output alone

Coordinates are not tracking. Aggregate/tabular observations do not create action identity. Absence is not counterevidence.

## Product Status

Normalize the session result into one of:

- DISCOVERY_PASS_PLAN_ONLY
- POLICY_CORRECTION_PASS
- SPEC_ONLY
- SPEC_CORRECTION_ACCEPTED
- SMOKE_PASS
- REVIEW_REQUIRED
- FAIL_CLOSED
- WAITING_OPERATOR_SELECTION
- RELEASE_CANDIDATE_NOT_PRODUCTION_BOUND
- ACTIVE_MATCH_EVIDENCE_PASS
- PRODUCTION_RELEASE

Explain why.

## Files / Artifacts

For each file write:

- file path
- role
- status
- authority class
- runtime authority: yes/no
- product code: yes/no
- current consumer if known
- GitHub productization needed: yes/no

Historical or legacy filenames containing `event_only` may be recorded unchanged for lineage. Their name alone does not make them current Event-Only product authority.

## Open Items

Separate open items into:

### Real gaps

Items that block product progress.

### Intentional waits

Valuable items waiting for upstream modules.

### Research backlog

Ideas not ready for productization.

### GitHub gaps

Branches, PRs, files or modules not yet in main.

### Unknown authority / consumer gaps

Items whose current consumer, runtime binding or authority cannot yet be proven. Do not resolve them by assumption.

## Next Correct Step

Give exactly one next step.

It must be executable and ordered.

Do not list ten alternatives.

Use the sequence:

`UNKNOWN → SEARCH EXISTING EVIDENCE → FRESH VERIFY IF CURRENT CLAIM → ACT`

## Handoff Block

End with a compact handoff block that can be pasted into a new ChatGPT session.

Include:

- current repo/development state, freshly verified if claimed current
- last exact physical ACTIVE_MATCH head separately
- current product priority/WIP
- source authority rule
- observation/capability admission rule
- active blockers
- next safe action
- merge/release state

## Output Rules

Write in Turkish.

Use direct, operational language.

Do not claim background work.

Do not claim GitHub write unless a GitHub write actually happened.

Do not claim ACTIVE_MATCH validation unless ACTIVE_MATCH execution actually happened for that exact implementation head.

Do not call visible rows canonical events.

Do not convert event-specific behavior into a product-wide Event-Only ontology.

Always distinguish:

- engineering evidence
- analyst evidence
- source authority
- observation capability/admission
- claim boundary
- release status

Default locks unless fresh evidence proves otherwise:

- `canonical_event_count=UNKNOWN`
- `true_action_count=UNKNOWN`
- `production_release=false`
