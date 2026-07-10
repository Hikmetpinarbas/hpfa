# HPFA Deterministic Analysis Command Runtime V1

## Purpose

Execute analyst-style commands without an AI runtime. The product reads raw JSON/CSV event rows, validates them, dispatches a deterministic calculator, and emits auditable JSON.

## Command contract

- RAW-PARSER
- MATH-METRIC
- TACTIC-MATRIX
- DEFENSIVE-ACTION-HEIGHT-PROXY
- XT-MATRIX
- RAW-DEBUG

## Internal event record

Required base fields:

- event_type
- team_id
- player_id
- timestamp_s or minute
- x
- y

Pass and carry additionally require end_x and end_y. Pass requires an explicit outcome. Coordinates use a 105 x 68 metre pitch.

## Mathematical models

Shot distance:

distance = sqrt((105 - x_normalized)^2 + (34 - y)^2)

Shot angle is the angle between vectors from the shot location to the two goal posts, computed with atan2(abs(cross), dot).

Heuristic xG candidate:

p = 1 / (1 + exp(-z))

z = intercept + beta_distance * distance + beta_angle * angle_rad

Default coefficients are deliberately marked HEURISTIC_UNCALIBRATED. They are not validated xG until fitted and calibrated on an owned shot/outcome corpus.

PPDA event proxy:

opponent passes in the opponent actor-frame first 60 percent
divided by
defending-team tackle + interception + foul actions in the geometrically equivalent zone.

A zero denominator returns null and INSUFFICIENT_DENOMINATOR.

Defensive action height proxy is the arithmetic mean of normalized x coordinates for tackle, interception and foul records. It is not defensive line height or off-ball shape.

Fixed-grid xT candidate uses a deterministic 12 x 8 matrix. Successful passes and carries receive end-cell value minus start-cell value. It is not validated xT until fitted on an owned transition/goal corpus.

## Claim boundary

- canonical_event_count remains UNKNOWN
- PPDA is an event-only pressing-activity proxy
- defensive action height is not defensive line truth
- heuristic xG is not calibrated xG
- fixed-grid xT is not learned action-value truth
- no coach intent, dominance, control, off-ball, fatigue or causal truth
- no production release claim

## Runtime position

raw surface -> validated event records -> command router -> metric calculation -> claim boundary -> JSON audit

No football analytics package, wrapper, external data API or AI runtime is required.

