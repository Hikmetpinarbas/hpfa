# HPFA PROJECT LOGBOOK PROMPT — SHORT

Use this prompt at the end of every HPFA work session.

Produce a project logbook entry in Turkish.

HPFA = Hikmet Pınarbaş Football Analytics.

HPFA is an event-only, claim-safe, modular and portable Football Intelligence Platform.

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

Only runtime/active_single_match/current can be runtime match truth.

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

Do not emit:

- dominance truth
- coach intention
- off-ball structure
- pitch control
- body orientation
- fatigue truth
- tactical plan truth
- canonical event count before Canonical Event Lite
- clean phase truth before claim gate

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
- runtime authority: yes/no
- product code: yes/no
- GitHub productization needed: yes/no

Example:

File: hpfa_event_only_rhythm_evidence_stack_v12.md
Role: rhythm apparatus spec
Status: SPEC_CORRECTION_ACCEPTED
Runtime authority: no
Product code: no
GitHub productization needed: yes, later

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

## Next Correct Step

Give exactly one next step.

It must be executable and ordered.

Do not list ten alternatives.

Examples:

Create Product Governance Runtime Pack V1 files in Termux, then prepare them for hpfa product repo intake.

or:

Write ACTIVE_MATCH Analyst Report Lite V1 contract before coding the module.

## Handoff Block

End with a compact handoff block that can be pasted into a new ChatGPT session.

Include:

- current repo state
- current Termux artifacts
- current product priority
- source authority rule
- active blockers
- next command

## Output Rules

Write in Turkish.

Use direct, operational language.

Do not claim background work.

Do not claim GitHub write unless a GitHub write actually happened.

Do not claim ACTIVE_MATCH validation unless ACTIVE_MATCH execution actually happened.

Do not call visible rows canonical events.

Always distinguish:

- engineering evidence
- analyst evidence
- source authority
- claim boundary
- release status
