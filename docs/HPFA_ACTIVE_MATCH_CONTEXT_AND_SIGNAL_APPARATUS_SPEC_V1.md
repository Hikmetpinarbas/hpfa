# HPFA Active Match Context + Signal Apparatus Spec V1

Status: PLAN_TO_EXECUTABLE_CANDIDATE  
Runtime authority: runtime/active_single_match/current/raw  
Claim layer: CLOSED  
Report language: CLOSED  

## Purpose

This apparatus standardizes match context and rhythm/signal profiling before downstream phase, sequence, pattern, momentum, failure, opportunity, and match identity engines.

HPFA must not analyze a match as one flat timeline. Every event-derived surface must preserve:

- score state
- first half / second half
- stoppage time
- card state
- numerical state
- substitution markers
- home/away state
- coordinate scale
- surface row authority

## Required Context Fields

- match_id
- source_surface_family
- source_file
- surface_row_id
- half
- period_scope
- stoppage_state
- start
- end
- absolute_time_seconds
- half_time_seconds
- team
- opponent
- home_away_state
- score_state
- goal_state
- yellow_card_state
- red_card_state
- numerical_state
- substitution_state
- coordinate_scale
- claim_safety

## Sequence Boundary Rules

A sequence must close on:

- half_change
- score_state_change
- red_card_state_change
- numerical_state_change
- restart_change
- break_event
- possession/team change
- end_of_chain

No possession or sequence may cross first-half to second-half boundary.

## Signal-Processing Boundary

Median and Savitzky-Golay smoothing are display-only unless calibrated.

Entropy must be computed on raw event/transition sequences, not on smoothed output.

STFT/spectrogram output is exploratory diagnostic only until calibrated against a baseline.

Allowed labels:

- sterile_circulation_candidate
- chaos_noise_candidate
- controlled_low_entropy_candidate
- high_variance_transition_candidate

Blocked labels:

- dominance truth
- tactical superiority truth
- pitch control truth
- coach intention
- fatigue truth
- off-ball structure truth

## Product Meaning

This apparatus lets HPFA distinguish:

- sterile possession vs controlled possession
- chaotic event noise vs valid high-tempo transition
- first-half behavior vs second-half adaptation
- normal 11v11 behavior vs red-card/numerical-state distortion
- score-driven behavior vs stable team identity

