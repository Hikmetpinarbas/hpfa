# HPFA — RDC Pro Remote Engineering Channel Policy v1

Status: ACTIVE ENGINEERING POLICY  
Date admitted: 2026-09-21  
Scope: development, maintenance, diagnostics, runtime verification and recovery operations  
Product authority impact: NONE

## 1. Purpose

Remote Desktop Commander (RDC) is admitted as a remote engineering / SRE / maintenance channel for HPFA-related phone and Termux work.

Observed account state on 2026-09-21:
- plan: Pro
- subscription: active
- tool-call allowance: unlimited while the Pro entitlement remains active
- account-side renewal date observed by the operator: 2026-10-21

This subscription state is operational context, not permanent repository truth. It must be re-verified when relevant.

## 2. Authority boundary

RDC is an access and execution channel. It is not an HPFA evidence or product authority.

RDC MUST NOT replace or supersede:
- GitHub for repository/code history and reviewed code state
- ACTIVE_MATCH for physical single-match runtime authority
- HPFA Truth Locks / Evidence Spine / ZFGV governance
- test results for harness-scoped behavioural claims
- runtime evidence for actual-execution claims

Truth lock:
RDC ACCESS != HPFA AUTHORITY

## 3. Permitted use

RDC may be used for:
- filesystem inspection and controlled edits
- Termux/package/tool installation
- process, tmux, cron and watcher management
- log inspection and diagnostics
- runtime acceptance checks
- Phone Doctor / Workspace Doctor execution
- local build orchestration
- recovery / backup verification
- repeatable static/runtime audits
- operational evidence collection needed to validate a scoped engineering claim

Use the full verification loop when practical:

INSPECT -> DIAGNOSE -> CHANGE -> TEST -> RUNTIME VERIFY -> REGRESSION CHECK -> RECOVERY -> AUDIT

## 4. Development advantage

While Pro unlimited calls are active, operators may use deeper verification rather than stopping at a single superficial check.

Preferred pattern:
- batch discovery first
- targeted intervention second
- concise verification third
- avoid unnecessary repeated calls that add latency/noise without information gain

Unlimited calls do not justify uncontrolled breadth.

## 5. Product independence

HPFA must continue to function if RDC is:
- offline
- disconnected
- downgraded
- rate-limited
- unavailable
- replaced by another remote engineering channel

No core HPFA algorithm, evidence rule, analysis output, ACTIVE_MATCH process or release condition may depend on RDC availability.

Truth lock:
REMOTE ENGINEERING AVAILABILITY != PRODUCT CAPABILITY

## 6. Write and release governance

RDC may modify local working trees when explicitly authorized by the user/operator scope.

Existing HPFA release governance remains unchanged:
- no silent release
- no automatic merge
- no production declaration from an RDC action
- no force push / destructive reset as a convenience shortcut
- fresh head / worktree state must be checked before writes when concurrent operators may exist

RDC success alone does not prove repository or production success.

## 7. Security / credential hygiene

RDC searches must be scoped to the task.

Do not broadly scan unrelated credential/config surfaces merely for convenience.
Do not copy secrets, tokens, passwords, keystores or refresh tokens into:
- repository files
- logs intended for sharing
- reports
- chat summaries
- generated documentation

If a tool result exposes unrelated secrets incidentally, they must not be propagated.

## 8. Evidence classification

RDC can collect repository, test and runtime evidence, but the channel itself is not the evidence claim.

Examples:
- file exists via RDC -> repository/filesystem observation
- test executed via RDC -> test-result surface
- service answers health endpoint via RDC -> runtime observation

Do not collapse these surfaces.

## 9. Failure handling

If RDC becomes unavailable:
- preserve current runtime
- avoid creating a parallel control owner
- use existing local Phone/Termux automation
- resume remote engineering after access is restored

No-visible-RDC-followup != HPFA failure.

## 10. Decision value

RDC Pro should be considered during HPFA development planning because it materially lowers the operational cost of:
- repeated diagnostics
- multi-step verification
- remote runtime acceptance
- maintenance
- recovery testing

It should be exploited as infrastructure leverage, not embedded as a product dependency.
