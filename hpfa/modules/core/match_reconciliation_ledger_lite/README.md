# Match Reconciliation Ledger Lite V2

Purpose: reconcile the same visible reciprocal process evidence from team → player → team without creating a second football reality.

Core invariants:
- one reciprocal process edge has one shared identity across forward/reverse views;
- one player may have many traces inside one process, but trace multiplicity never inflates process or episode counts;
- team episode count is a unique episode-ID union;
- player episode sets are unioned back to the team set; player membership sums are never treated as team episode counts;
- anchor, opponent response and counter-response memberships remain separate roles;
- player/process membership is participation evidence, not player quality or tactical importance;
- unresolved episode binding remains REVIEW_REQUIRED and is never fabricated.

Current scope:
- reciprocal edge consistency;
- team episode union accounting;
- player process/episode membership;
- player → team episode-union reconciliation.

Still explicit NOT_EVALUATED:
- loss↔recovery reconciliation;
- shot↔goalkeeper reconciliation;
- team-conditioned phase/activity reconciliation;
- final professional finding.

Claim locks:
- canonical_event_count=UNKNOWN
- true_action_count=UNKNOWN
- production_release=false
- no possession/phase/sequence/tactical/causal truth
