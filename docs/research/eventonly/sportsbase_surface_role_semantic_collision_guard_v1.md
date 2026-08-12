# SportsBase Surface-Role Semantic Collision Guard V1

Status: `POLICY_CORRECTION_REQUIRED / ACTIVE_MATCH_SEMANTIC_COLLISION_CONFIRMED / CURRENT_HEAD_CI_REQUIRED / ACTIVE_MATCH_REVALIDATION_REQUIRED / NOT_PRODUCTION`

Issue: #242

## Purpose

Prevent SportsBase surface labels whose meaning changes by source role from being promoted into the wrong action family.

This correction is deliberately narrow. It does not create canonical events, does not validate provider metric definitions, and does not rename ambiguous provider labels into new truth.

## Runtime authority

The only match truth is:

`runtime/active_single_match/current`

External match audits, Google Drive, Dropbox and donor repositories are `REFERENCE_ONLY / DONOR_SUPPORT`.

## Confirmed ACTIVE_MATCH diagnosis

The current pre-correction action-bundle surface contains:

```text
RESTART action_bundle total = 1126
TEAM_SURFACE_CANDIDATE RESTART = 1108
GOALKEEPER_SURFACE_CANDIDATE RESTART = 18
```

The provider-label surface contains:

```text
TEAM Goal kicks short (0-15 m) = 611 surface rows
TEAM Goal kicks medium (15-40 m) = 440 surface rows
TEAM Goal kicks long (40+ m) = 58 surface rows
GOALKEEPER Goal kicks = 18 surface rows
GOALKEEPER Goal kicks short = 4 surface rows
GOALKEEPER Goal kicks medium = 3 surface rows
GOALKEEPER Goal kicks long = 11 surface rows
```

The current contamination is therefore a source-role semantics defect, not an event-counting proof. `canonical_event_count=UNKNOWN` remains mandatory.

## Corrected source-role contract

### Goalkeeper surface

For `GOALKEEPER_SURFACE_CANDIDATE`:

```text
Goal kicks
Goal kicks short (0-15 m)
Goal kicks medium (15-40 m)
Goal kicks long (40+ m)
```

remain exact reviewed candidates for:

```text
semantic_role=ACTION_ANCHOR
action_family=RESTART
restart_type=GOAL_KICK
downstream_eligibility=ACTION_CANDIDATE_ELIGIBLE
```

Length variants retain `SHORT / MEDIUM / LONG` as candidate distance qualifiers.

### Team surface length labels

For `TEAM_SURFACE_CANDIDATE`:

```text
Goal kicks short (0-15 m)
Goal kicks medium (15-40 m)
Goal kicks long (40+ m)
```

are policy-corrected to:

```text
semantic_role=ATTRIBUTE_REFERENCE
action_family=PASS
distance=SHORT|MEDIUM|LONG
action_subtype=PASS_DISTANCE_ATTRIBUTE_CANDIDATE
restart_type=NULL
downstream_eligibility=REFERENCE_ONLY
semantics_decision=CONTEXT_DEPENDENT_SEMANTIC_COLLISION
```

`PASS` here is a controlled action-family candidate used to preserve the observed pass-distance relationship. It is not a validated provider-definition truth and it is not a canonical rename.

### Plain TEAM `Goal kicks`

No exact TEAM rule is asserted. Without reviewed role-specific evidence it must fall to the existing token-fallback review path and remain blocked from action admission.

### Unexpected player surface

No exact player rule is asserted for the length labels. Existing fail-closed/token-fallback review behavior is preserved.

## Evidence routing

`ATTRIBUTE_REFERENCE` is admitted only as:

```text
ATTRIBUTE_REFERENCE
→ REFERENCE_ATOM
→ REFERENCE_ROUTE
```

It must never become:

```text
ACTION_ANCHOR_ATOM
TEAM_ACTION_REFLECTION_ROUTE
GOALKEEPER_ACTION_ROUTE
PRIMARY_ACTION_ANCHOR_ROUTE
```

Therefore TEAM goal-kick-length rows remain visible evidence without creating `RESTART` action bundles.

## Reference/donor support

A separate SportsBase match-surface semantic audit showed the TEAM length labels co-occurring with ordinary pass surface and appearing across the pitch. This supports a semantic-collision candidate but does not become ACTIVE_MATCH truth.

Dropbox SportsBase donor material supports raw action/coordinate surfaces and fail-closed interpretation under semantic ambiguity. Google Drive and donor-repo review did not provide a provider-official exact definition proving that TEAM length labels are literal goal kicks.

Accordingly:

```text
observed surface evidence != reviewed provider-definition evidence
```

## ACTIVE_MATCH acceptance

Current-head runtime evidence must demonstrate, without hardcoded match identity or row totals:

```text
TEAM goal-kick-length RESTART action_bundle count = 0
TEAM goal-kick-length reference/attribute evidence preserved > 0
GOALKEEPER goal-kick candidate evidence preserved > 0
canonical_event_count=UNKNOWN
production_release=false
```

The final corrected RESTART total must be derived from the runtime surface. Product code must not hardcode the expected total.

## Downstream boundary

Until current-head CI and ACTIVE_MATCH revalidation pass:

- PR #241 coordinate-frame recheck remains draft/open;
- its goalkeeper-scoped anchor algorithm is not invalidated by this correction;
- issue #226 progression recheck remains blocked;
- no progression truth or line-break truth may be emitted from the contaminated upstream action-bundle surface.

## Claim ceiling

```text
validated_provider_semantics=false
validated_provider_goal_kick_definition=false
pass_distance_truth=false
canonical_event_count=UNKNOWN
progression_truth=false
line_break_truth=false
tactical_truth=false
production_release=false
```
