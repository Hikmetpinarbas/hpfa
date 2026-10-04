# HPFA Controlled Commercial Pilot — Red Team Checklist V1

This checklist is a release-readiness adversarial review for a controlled commercial pilot. It does not authorize PRODUCTION_RELEASE.

## Evidence authority

- Exact delivered head is recorded.
- GitHub engineering checks belong to that exact head.
- Physical ACTIVE_MATCH acceptance belongs to that exact head.
- Three-profile portability acceptance belongs to that exact head.
- Old CI, old ACTIVE_MATCH and old portability evidence are not reused as current truth.

## Football-claim safety

- canonical_event_count remains UNKNOWN unless explicitly proved.
- true_action_count remains UNKNOWN unless explicitly proved.
- ROW != EVENT TRUTH.
- MULTIFORMAT != INDEPENDENT EVIDENCE.
- SAME TIMESTAMP != TOTAL ORDER.
- COORDINATE != TRACKING.
- PROCESS LABEL != COACH INTENTION.
- RECURRENCE != CAUSALITY.
- MODEL OUTPUT != FACT.
- ABSENCE != COUNTEREVIDENCE.
- 0 professional EMIT remains a valid outcome.
- Analyst-facing narrative cannot upgrade a non-admitted finding.

## Human output

- Evidence completeness is visible.
- REVIEW_REQUIRED is not hidden by polished prose.
- Counterevidence / withdrawal conditions remain visible where available.
- Fact-only rendering is not labelled as a professional finding.
- If professional_emit_allowed_count = 0, the analyst report is visibly labelled as review narrative.

## Portability

- Rich package executes.
- Degraded package executes or degrades explicitly without false-strength claims.
- Different-profile package executes.
- Match/team/player/sample identity is not hard-coded into product logic.
- Missing optional surfaces affect only dependent constructs.

## Commercial bundle

- Raw provider match data is absent.
- Raw donor/vendor source is absent.
- runtime/, data/, vendor/, out/, build/, _diag/ and tests are absent.
- Third-party runtime packages are not bundled.
- LICENSE, NOTICE and THIRD_PARTY_NOTICES are present.
- Controlled-pilot policy and quickstart are present.
- Bundle is deterministic and carries exact-head identity.

## Commercial boundary

- commercial scope = ASSISTED_CONTROLLED_PILOT.
- production_release=false.
- public package-index upload remains unauthorized.
- Customer/provider is responsible for lawful access to match data.
- HPFA software ownership is not presented as provider-data redistribution authority.

## Pass rule

Red Team PASS requires zero critical blockers. Any unresolved item affecting evidence authority, exact-head identity, claim ceiling, data rights, bundle contents or physical execution => REVIEW_REQUIRED.
