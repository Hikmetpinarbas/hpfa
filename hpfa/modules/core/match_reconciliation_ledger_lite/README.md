# Match Reconciliation Ledger Lite V1

Claim-safe bidirectional reconciliation over the same reciprocal evidence graph.

Core invariants:
- forward and reverse team views reuse one edge identity;
- team episode counts use unique episode-ID union, never player-membership sums;
- annotation multiplicity never creates occurrence multiplicity;
- player/team, loss/recovery, shot/GK and phase reconciliation stay unevaluated until their upstream relation surfaces are explicitly bound;
- no possession, phase, tactical, causal, canonical-event or production truth is opened.

Release locks:
- canonical_event_count=UNKNOWN
- true_action_count=UNKNOWN
- production_release=false
