# Analyst Presentation View Model Lite V1

Module id: `analyst_presentation_view_model_lite_v1`

## Purpose

Expose current HPFA runtime artifacts as a thin-client presentation contract.
It does not create football evidence, new semantics, tactical truth, chronology truth or production output.

## Product role

This is a P7/P8 bridge toward future web/mobile clients.
It does not authorize P10 mobile-client release.

Core invariant:

```text
VISUAL_STRENGTH <= EVIDENCE_STRENGTH
```

## Input authority

Only current HPFA output artifacts under the selected output root are read.
No Drive, donor, archive or external research source becomes runtime truth.

## Surface states

Each analyst-facing surface must explicitly resolve to one of:

```text
AVAILABLE
DEGRADED
MISSING
NOT_EVALUATED
FAIL_CLOSED
```

The V1 contract exposes:
- Analyst Report
- Match Story
- Six-Phase Match View
- Mechanism Cards
- Player Process Cards
- Counterevidence Cards
- Observed Replay
- Traceback / Evidence Drawer
- Broadcast Summary
- Unknown / Unobservable Register

Missing capability must stay visible. The client may not interpolate it.

## Safety rules

- RECORDED_ACTIONS_ONLY.
- Event-anchor connection is not ball trajectory.
- Episode candidate is not tactical episode truth.
- Process participant is not off-ball tactical role.
- Same timestamp does not create total order.
- Phase candidate is not six-phase truth.
- Interaction provenance cannot strengthen football evidence.
- Client code cannot create new football semantics.
- canonical_event_count remains UNKNOWN unless separately admitted.
- true_action_count remains UNKNOWN unless separately admitted.
- production_release remains false.

## Traceability

V1 provides artifact-level provenance with size and SHA-256.
Observation-level deep links are explicitly a later contract.

## Bundle integration

The standard ACTIVE_MATCH bundle must include:

```text
analyst_presentation_view_model_lite_v1.json
```

The view model is a standard deliverable, not a replacement for:
- full-spine runtime evidence
- analyst report
- bundle manifest
- report-output governance
- final-report assembly gate

## Acceptance

Minimum:
1. deterministic same-input output;
2. FAIL_CLOSED when full-spine artifact is absent;
3. missing/degraded surfaces remain explicit;
4. no claim-ceiling promotion;
5. view model included in standard user bundle;
6. production_release=false.

PASS != RELEASE.
Mobile application release is not granted by this contract.

## Match Story / Mechanism compression extension

The presentation layer may group current intelligence chains only by an already-admitted upstream tuple:

```text
argument_family + relation_scope + analysis_route
```

This grouping is presentation compression, not discovery of a new football mechanism.

The Match Story target is 3–5 distinct mechanism families only when the admitted runtime actually contains that many distinct families.
A forced minimum is forbidden.

If only one distinct family is admitted, the correct product output is one mechanism card.

Mechanism-card nominal chain counts are navigation/coverage counts only.
They are not independent recurrence, probability, confidence, evidence strength or causal weight.

Each mechanism card must preserve:
- upstream process/argument family
- relation scope
- analysis route
- nominal chain count
- distinct packet/context/support reference counts
- defeasible state distribution
- independence states
- counter-scenarios
- withdrawal conditions
- safe-sentence examples
- explicit cannot-say register

Selection basis:

```text
COVERAGE_COMPRESSION_NOT_EVIDENCE_STRENGTH
```

Forbidden:
- inventing extra mechanism families to reach 3–5
- treating nominal chain count as independent support
- ranking mechanism truth strength from UI coverage
- causal, tactical-intention, off-ball, pressure-geometry or dominance promotion

## Player Process Card extension

Player Process Cards consume only current-invocation:
- match-local identity candidates
- trackable action trace candidates
- trackable action consequence candidates

They represent recorded-action participation, not off-ball tactical role.

Required visible guards:
- identity_scope=MATCH_LOCAL_CANDIDATE_ONLY unless separately admitted
- validated_player_identity flag
- trace_candidate_count_is_physical_action_count=false
- process_participation_is_off_ball_tactical_role=false

Allowed card content:
- match-local actor display candidate
- team identity candidate
- trace-candidate count
- action-family candidate distribution
- source-role distribution
- period distribution
- consequence-candidate record distribution
- count of trace records with visible follow-up support
- representative trace candidate IDs

Blocked interpretation:
- player quality from trace volume alone
- physical action count
- off-ball tactical role
- positioning truth
- pressure geometry
- workload, speed or distance truth
- coach intention

The surface remains DEGRADED while identity is match-local candidate only and higher-level admitted process participation is unavailable.

## Traceback / Evidence Drawer extension

The presentation layer now exposes a reference-ID traceback graph.

Episode links:
episode_candidate_id
→ context refs
→ row nucleus refs
→ action-occurrence eligible context refs
→ support-only / review-debt refs

Mechanism links:
mechanism candidate
→ argument ids
→ packet ids
→ context refs
→ supporting refs
→ contradicting refs

Player links:
match-local actor candidate
→ trackable action trace ids
→ consequence candidate ids
→ supporting evidence atom ids

Scope:
REFERENCE_ID_GRAPH_ONLY_NOT_RAW_ROW_RENDER

This layer does not reinterpret source rows, create new chronology or create football semantics.
It provides analyst navigation and provenance only.

## Graphability contract

Every analyst-facing construct must explicitly declare one of:

- GRAPHABLE
- GRAPHABLE_AS_COMPANION_ONLY
- UNGRAPHABLE_WITH_CURRENT_DATA

No construct may be forced into a misleading chart merely to satisfy visualization coverage.

Global invariant:

```text
VISUAL_STRENGTH <= EVIDENCE_STRENGTH
```

Current preferred representations:
- Match Story -> horizontal bar of nominal chain coverage by distinct admitted mechanism family
- Mechanism Cards -> stacked bar of defeasible-state distribution
- Player Process Cards -> grouped/small-multiple bars of recorded action-family candidate counts
- Observed Replay -> interval strip with unordered same-time bundles
- Six-Phase Match View -> bar of phase-activity candidate labels, never phase truth
- Counterevidence -> horizontal bars of nominal counter-scenario / withdrawal-condition mentions
- Traceback -> node-link or hierarchical drill-down
- Broadcast Summary -> count badge/bar only after editorial grouping
- Unknown/Unobservable Register -> bar of epistemic surface states
- Analyst Report prose -> companion charts only; prose itself is not converted into numeric chart truth

Every graph spec must carry forbidden_visual_inference fields.
Examples:
- nominal chain count != evidence strength
- trace volume != player quality
- interval != possession truth
- candidate label != phase truth
- reference density != truth strength
- absent counterevidence != support

If the required denominator, temporal order, identity, relation, or observation surface is missing, graphability must downgrade instead of interpolating.

## Broadcast compression extension

Broadcast candidates are compressed deterministically by:
- upstream argument family
- defeasible state

The compressed group exposes:
- argument_family
- defeasible_state
- nominal_candidate_count
- review_required_count
- one deterministic representative safe-sentence candidate
- explicit non-independence guard

Representative sentence selection is deterministic:
shortest safe sentence within the same family/state group.

This is compression, not editorial publication.
The representative sentence is not final broadcast copy.

Blocked interpretations:
- nominal candidate count as evidence strength
- nominal candidate count as independent recurrence
- SUPPORTED as publication permission
- candidate-pool size as match importance

Graph:
STACKED_OR_GROUPED_BAR_BY_FAMILY_AND_DEFEASIBLE_STATE

## Six-Phase presentation extension

The six canonical analyst slots remain:
- YERLESIK_HUCUM
- GECIS_HUCUMU
- YERLESIK_SAVUNMA
- GECIS_SAVUNMASI
- DURAN_TOP_HUCUMU
- DURAN_TOP_SAVUNMASI

A slot may only be:
- PROXY_LENS_ONLY
- NOT_EVALUATED

Current proxy mapping:
- circulation / advanced access / terminal activity candidates -> YERLESIK_HUCUM proxy lens
- recovery-transition activity candidate -> GECIS_HUCUMU proxy lens
- loss-transition activity candidate -> GECIS_SAVUNMASI proxy lens
- settled defence and set-piece phases remain NOT_EVALUATED without admitted upstream support

This mapping does not create phase truth, possession truth or tactical truth.

Counts are source activity LABEL MENTIONS, not:
- episode counts
- duration shares
- possession shares
- independent recurrence counts
- tactical dominance

Graph:
SIX_SLOT_STATUS_BAR_OR_MATRIX

Any future stronger six-phase representation requires explicit denominator/time/phase admission.

## Mechanism WHERE / WHEN binding extension

Mechanism presentation may bind existing upstream references to time and spatial anchors only through current admitted reference chains.

WHEN source:
mechanism argument
→ packet
→ input_window_records
→ period_candidate + start_candidate + window ref

WHERE source:
mechanism argument
→ packet
→ input_sequence_records
→ visible_action_sequence_candidate
→ trackable_action_trace_candidate_ids
→ recorded coordinate anchors

No new zone ontology, path or tactical geometry is created.

Graph forms:
- WHEN -> TIME_ANCHOR_STRIP
- WHERE -> COORDINATE_ANCHOR_SCATTER

Graph data source-of-truth remains inside:
surface_data.mechanism_cards[*].where_when

Graphability specs use data_ref pointers rather than duplicating anchor payload.

Hard guards:
- time anchor != episode duration
- same timestamp != total order
- anchor density != mechanism strength
- anchor coverage != independent recurrence
- coordinate anchor connection != ball trajectory
- coordinate distribution != team shape
- coordinate density != pitch control
- recorded coordinate != off-ball positioning truth
- broad spatial/temporal coverage != causal mechanism truth

If WHERE/WHEN anchors cover large portions of the match, the presentation must describe this as broad coverage, not strong recurrence.

Coordinates are normalized to numeric values for graph rendering when parseable.
Unparseable coordinates are omitted from the graph anchor surface rather than coerced.

## Mobile lazy graph delivery for mechanism WHERE / WHEN

Full WHERE/WHEN anchor arrays are not duplicated inside graphability specs.

The analyst presentation view-model carries:
- exact time_anchor_count
- exact spatial_anchor_count
- period candidates
- coordinate-evidence-status counts
- bounded samples (12 time + 12 spatial anchors)
- lazy graph source contract
- graph representation contract

Delivery mode:
LAZY_REFERENCE_JOIN

Full WHEN data is reconstructed on demand from:
active_match_full_spine_v1.json
→ intelligence_chains[*].packet.input_window_records

Full WHERE data is reconstructed on demand from:
packet.input_sequence_records.sequence_id
→ visible_action_sequence_candidates_lite_v1.json
→ trackable_action_trace_candidate_ids
→ trackable_action_trace_candidates_lite_v1.json
→ pos_x_candidate / pos_y_candidate

This is a delivery optimization only.
It does not change the evidence spine or claim ceiling.

Real ACTIVE_MATCH acceptance:
- time anchors: 1003
- spatial coordinate anchors: 1125
- coordinate evidence status: COORDINATE_PRESENT for 1125 anchors
- periods visible: 1 and 2
- same-timestamp total ordering remains forbidden
- path_or_trajectory_truth=false
- coverage_is_independent_recurrence=false

Presentation payload observed before lazy optimization:
5,121,039 bytes

After lazy optimization:
2,510,787 bytes (~2.394 MB)

The reduction is approximately half while preserving exact counts, graphability, samples and traceback paths.

Mobile use:
- initial card render uses summary + sample
- tap/open WHERE/WHEN graph triggers lazy reference join
- full evidence remains available without burdening first-frame payload

## Mechanism WHERE / WHEN reference binding

Mechanism cards may expose WHERE / WHEN only through existing upstream reference membership.

WHEN:
- packet.input_window_records
- period_candidate
- start_second_candidate
- layer_state

WHERE:
packet.input_sequence_records.sequence_id
→ visible_action_sequence_candidate_id
→ trackable_action_trace_candidate_ids
→ recorded trace coordinate candidates

Important ceiling:
visible sequence candidate membership is NOT sequence truth.
A trace may have sequence_link_allowed=false.
Therefore spatial anchors are reference-reached recorded coordinate anchors only.

Explicitly forbidden:
- joining coordinate anchors into ball trajectory
- inferring team shape
- inferring pitch control
- inferring off-ball positioning
- treating same timestamp as total order
- treating anchor density as mechanism strength
- treating nominal anchor coverage as independent recurrence

Claim ceiling:
MECHANISM_WHERE_WHEN_REFERENCE_BINDING_ONLY

Mobile delivery:
LAZY_REFERENCE_JOIN

The view model carries:
- exact anchor counts
- period coverage
- coordinate evidence status counts
- bounded samples
- lazy source join descriptors

It does not inline the complete coordinate/time population into each mechanism card.

Graph contracts:
WHEN -> TIME_ANCHOR_STRIP
WHERE -> COORDINATE_ANCHOR_SCATTER

Graph samples are previews only.
Full graph retrieval must follow the declared lazy join paths.

Six-phase count terminology:
source_activity_label_mention_count is used because multiple activity labels may coexist in one episode candidate.
It is not an episode denominator, time share, possession share or independent recurrence count.

## Comparative graph cards

Comparative views are compressed into mobile and broadcast graph cards.

Policy:
COMPACT_COMPARISON_WITH_VISIBLE_DENOMINATOR_AND_NO_EVALUATIVE_VERDICT

Current cards:
- period mechanism anchor comparison
- team-candidate coordinate anchor comparison
- defeasible-state comparison
- zone mentions by period
- channel mentions by period

Every card must preserve:
- graph type
- raw rows
- eligible denominator where defined
- claim ceiling
- broadcast copy candidate
- broadcast_copy_is_final=false

Broadcast copy candidates are explanatory metadata, not final editorial sentences.

Blocked:
- better/worse verdict from count difference
- causal interpretation
- rate/share inference without eligible denominator
- identity promotion
- independent recurrence inference from nominal counts

## Chart render pack

The presentation view-model now emits frontend-ready chart specs for the comparative cards.

State:
RENDER_READY

Current charts:
- period mechanism grouped bar
- team-candidate coordinate bar
- defeasible-state stacked bar
- zone-by-period grouped bar
- channel-by-period grouped bar

Render contract:
- DO_NOT_INTERPOLATE missing values
- preserve candidate / proxy language
- no percentages unless numerator + eligible denominator are explicitly defined
- client-defined colors are non-epistemic unless separately contracted
- frontend may not invent missing values
- frontend may not infer causality
- frontend may not connect spatial points as trajectory

Each chart retains its claim ceiling and denominator metadata.

## Analyst dashboard manifest

The presentation view-model now emits a dashboard layout manifest.

Reference design principle:
take the visual composition of a professional match-analysis dashboard, but never copy unsupported football truth.

Primary desktop regions:
- Match Story header
- schematic pitch replay canvas
- Six-Phase matrix
- match timeline
- process chain
- comparison panel
- truth / limits panel
- player process drawer
- evidence drawer

Mobile navigation:
MATCH_STORY → FIELD_REPLAY → SIX_PHASE → COMPARISONS → PLAYERS → COUNTEREVIDENCE → EVIDENCE

Field replay:
SCHEMATIC_PITCH_WITH_RECORDED_ANCHORS

Allowed:
recorded coordinate dots, episode/time labels, action-family labels, team-candidate markers, traceback highlights.

Blocked without stronger evidence:
invented ball trajectory, invented runs, team-shape polygons, pressure geometry, pitch-control surfaces, off-ball role paths.

Claim ceiling:
PRESENTATION_LAYOUT_ONLY_NO_NEW_EVIDENCE

## HPFA personal visual and cognitive doctrine

The analyst product must reflect the operator's established aesthetic and intellectual references as design principles, not literal collage.

Visual references:
- Caravaggio -> contrast and attention hierarchy
- Leonardo da Vinci -> geometry, proportion and mathematical structure
- Nikola Tesla -> electric energy and dynamic accent
- Giordano Bruno -> conceptual sharpness
- Eduardo Galeano -> human-scale football storytelling
- Raffaello Sanzio -> compositional focus and balance
- Hieronymus Bosch -> controlled complexity
- Umberto Eco -> layered meaning and progressive disclosure
- Samuel Beckett -> restraint, whitespace and tension where information is absent

Do not use literal portraits, old-book decoration, skulls, coils or historical cosplay as the default interface language.

Operator cognition:
- mechanism over scoreline
- evidence over rhetoric
- context over raw count
- counterevidence before confidence
- uncertainty visible
- deep reasoning, simple expression
- complex systems without false certainty

Avoid:
- surface-level commentary
- fan-style judgment
- empty enthusiasm
- ornamental complexity
- unverified claims
- blind composite scores
- aesthetic inflation of evidence

Palette:
dark navy / black base, electric blue primary accent, restrained green for support, restrained amber/red for warning.

Aesthetic quality must improve analyst comprehension without strengthening the underlying football claim.

## Depth model

The HPFA analyst dashboard uses three progressive depth layers.

L1 — MATCH READ
Target: 5–10 seconds.
Question:
What are the few visible match stories worth attention?
Show:
- Match Story
- Six-Phase state
- key comparisons
- safe meaning
- uncertainty marker
Do not flood with raw reference IDs or dense tables.

L2 — MECHANISM READ
Target: 30–120 seconds.
Question:
How did the visible mechanism unfold, where/when, through which players and variants?
Show:
- mechanism
- WHERE / WHEN
- episode/process chain
- successful / failed / deviant variants
- visible consequence
- recorded player participation
Never promote to trajectory, off-ball tactical role or coach intention.

L3 — EVIDENCE AUDIT
Target: on demand.
Question:
Why is the claim allowed, what weakens it, and when should it be withdrawn?
Show:
- support
- counterevidence
- dependency state
- uncertainty
- withdrawal condition
- traceback

Drill-down:
MATCH STORY
→ MECHANISM
→ WHERE / WHEN
→ VARIANT
→ PLAYER PARTICIPATION
→ CONSEQUENCE
→ COUNTEREVIDENCE
→ EVIDENCE TRACEBACK

Depth principle:
SIMPLE_FIRST_VIEW_DEEPER_ON_DEMAND_TRACEABLE_TO_EVIDENCE

Detail may collapse until requested.
Uncertainty may never be hidden.
UNKNOWN / NOT_EVALUATED / UNOBSERVABLE remain visible states.

## Donor-adapted visual epistemology

Donor sources inspected:
- HPFA Graphics Research Pack v1
- HP-Motor dashboard prototype
- HP-Engine PlotSpecFactory
- Dropbox Visual Constitution B02
- Dropbox Metric Visualization Grammar B04
- Dropbox Visual Forbidden Pattern Map B08
- Dropbox Professional Match Report safe-writing contracts

Decision:
ADAPT_NOT_COPY.

ADAPT_NOW:
1. Chart audit metadata:
   - what it measures
   - what it does not measure
   - denominator rule
   - observation window
   - source surface
   - claim ceiling
   - uncertainty note
2. Epistemic visual tokens:
   - OBSERVED
   - CANDIDATE
   - UNCERTAIN
   - COUNTEREVIDENCE
   - WITHDRAWN
   - MISSING_UNKNOWN
3. Visual drama cannot increase claim capacity.

ALREADY_ABSORBED:
- UI renders specs instead of creating football truth.
- no invented trajectory / shape / pitch-control.
- proxy and candidate language remains visible.
- denominator-visible comparison.

ADAPT_LATER:
- event-rhythm temporal charts
- regain/loss consequence distributions
- player action-location facets
only after construct-specific upstream admission.

REJECT / DO NOT REVIVE:
- event-derived compactness as physical compactness
- dominance heatmaps
- tracking-like player positions
- pressure truth glow
- opaque composite scores
- inferred receiver networks without admitted receiver identity

These donor decisions do not change source authority.
Donors remain SUPPORT/HISTORICAL.

## Football dynamics presentation surfaces

Three additional event-derived presentation surfaces are admitted when current-invocation trace and consequence artifacts exist.

### Visible action rhythm proxy
5-minute windows of nominal trackable trace-candidate counts.

Meaning:
visible recorded-action activity rhythm proxy.

Not:
- true match tempo
- physical intensity
- possession speed
- dominance

Trace counts remain non-physical-action counts.

### Loss / recovery visible consequences
TURNOVER and RECOVERY trace anchors are grouped by their current visible consequence candidates.

Meaning:
what became visibly observable after recorded loss/recovery anchors.

Not:
- causal effect
- pressing success
- transition quality fact
- tactical intention

### Player action-location candidates
Median x/y of recorded coordinate anchors by match-local actor candidate.

Meaning:
where the player's recorded actions occurred.

Not:
- player position
- team shape
- off-ball role
- compactness

Claim ceiling:
RECORDED_ACTION_LOCATION_CANDIDATE_ONLY

### Dashboard
A dedicated DYNAMICS navigation/region is available:
RHYTHM_CONSEQUENCE_AND_ACTION_LOCATION_VIEWS

### Render-ready charts
- activity rhythm by period
- turnover visible consequences
- recovery visible consequences
- player action locations

All inherit graph audit metadata and visual-strength <= evidence-strength rules.
