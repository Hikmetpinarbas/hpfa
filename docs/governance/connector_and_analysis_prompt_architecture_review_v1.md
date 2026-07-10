# HPFA Connector and Analysis Prompt Architecture Review V1

Status: `POLICY_CORRECTION_PASS`

## Product authority

```text
hpfa = only executable product repository
HP-Motor / HP-Engine / HP-PROJELERI / Drive / Dropbox / papers = donor or reference only
runtime/active_single_match/current = only match-truth authority
```

This document evaluates 20 proposed prompts as product architecture ideas.

Decision vocabulary:

```text
ACCEPT = product-aligned and high priority
ADAPT = useful core idea, but wording/authority/claim model must change
DEFER = valid later, blocked by upstream architecture
REJECT = violates HPFA authority, event-only boundary, claim safety or maintainability
```

## Executive decision

Accepted architecture spine:

```text
read-only donor discovery
-> reference isolation
-> immutable donor manifest
-> event-only eligibility gate
-> schema and provenance validation
-> mismatch / no-imputation fail-closed gate
-> extractable primitive mapping
-> dependency compatibility CI
-> canonical analysis candidate
-> claim-safe analyst output
```

Rejected architecture spine:

```text
donor data = fact
tracking/video import
binary certainty
silent imputation
connector outage prediction
mandatory tactical fix
socioeconomic context as causal football truth
black/white visualization certainty
```

## Prompt-by-prompt decisions

### 1. Read-only donor connector pipeline

Decision: `ACCEPT_WITH_ARCHITECTURE_CORRECTION`
Priority: P0 governance / P1 implementation

Current limitation:

HPFA has donor-role governance and donor-to-composite plans, but no executable connector permission boundary.

Better architecture:

```text
GitHub App / fine-grained token for donor repos:
  contents: read
  metadata: read
  pull requests: read
  issues: read only when required
  actions: none
  administration: none
  workflows: none

hpfa product token:
  scoped only to hpfa
  donor credentials never receive hpfa write access
```

Connector output is not copied donor code. It is a signed/hashed discovery manifest containing source path, source commit, file type, content hash and source role.

Product impact: high governance and reuse value.
Runtime dependency: internet/GitHub availability for discovery only; never match truth.
Claim impact: none directly.
Tests: permission negative tests, write-denial test, provenance hash test.
Release impact: governance/runtime tooling only; not football release.

### 2. L1 immutable donor data and ERR-101 Fusion Mismatch

Decision: `ADAPT`
Priority: P1 after connector contract

Reject the name `Binary Fusion`: donor references are not two truth sources to be merged as facts.

HPFA-native layers:

```text
R0 DONOR_REFERENCE_MANIFEST
R1 IMMUTABLE_REFERENCE_SNAPSHOT
R2 CAPABILITY_COMPARISON
R3 HPFA_NATIVE_ADAPTATION_CANDIDATE
```

`ERR-101: Fusion Mismatch` is acceptable only for contract/schema/capability disagreement, not football-event truth disagreement.

On mismatch:

```text
status=FAIL_CLOSED
decision=BLOCK_DONOR_ADAPTATION
error_code=ERR-101
no authority registry write
```

Tests: same-capability incompatible-schema fixture, hash mismatch, source-version mismatch, no downstream adaptation.

### 3. PR dependency compatibility CI

Decision: `ACCEPT`
Priority: P0/P1

High product leverage.

Every new analytic function must declare:

```text
required_primitives
required_columns
required_context
accepted_schema_versions
upstream_claim_ceiling
runtime_cost_class
```

CI compares this declaration against current HPFA connector/reference manifests and canonical product schemas.

Failure states:

```text
DEPENDENCY_MISSING
SCHEMA_VERSION_CONFLICT
UNDECLARED_PROVIDER_ALIAS
TRACKING_DEPENDENCY_REJECTED
CLAIM_CEILING_CONFLICT
```

Important correction: donor connector structures cannot define product dependency truth. The canonical HPFA schema remains authoritative.

### 4. Timeout / connection failure protocol

Decision: `ACCEPT`
Priority: P0

Required report format:

```text
Kritiklik
Neden
Çözüm
```

On `ConnectionError`, timeout or incomplete transfer:

```text
status=FAIL_CLOSED or DEGRADED_REFERENCE_ONLY
prediction_allowed=false
analysis_promotion_allowed=false
output="Eksik Veri/Bilinmiyor"
```

No cached donor reference may silently become current evidence.

### 5. Event-only file Claim Gate

Decision: `ADAPT`
Priority: P0/P1

Accept event-only eligibility, reject extension-only trust.

Allowed extensions as intake candidates:

```text
.csv
.xml
.xlsx
```

But extension is insufficient. The gate must inspect content/schema and reject:

```text
tracking frames
player trajectories
video files
video-derived coordinates
optical tracking packages
GPS/load/wellness payloads
```

Important authority correction: donor repositories are reference/capability sources, not ACTIVE_MATCH event truth. Event files become runtime candidates only through the declared active-match ingest path.

### 6. Reference Isolation Protocol

Decision: `ACCEPT`
Priority: P0

Recommended paths:

```text
references/donor_data/manifests/
references/donor_data/snapshots/
references/donor_data/quarantine/
```

Never import donor reference packages as executable Python modules.

Protected paths:

```text
docs/governance/runtime_pack_v1/source_role_registry.json
authority_registry/ if introduced
runtime/active_single_match/current
hpfa/modules/
```

Required controls:

```text
CODEOWNERS approval
path-policy CI
git diff scanner
forbidden symlink check
forbidden import check
provenance label requirement
```

No direct or transitive promotion from references to authority.

### 7. No Imputation Rule and L3 stop

Decision: `ACCEPT`
Priority: P0

If donor references or runtime candidate surfaces conflict or have missing required fields:

```text
imputation_allowed=false
canonical_promotion_allowed=false
analysis_allowed=false or explicitly degraded
missing_fields recorded
conflict_fields recorded
status=FAIL_CLOSED
```

No default value, nearest-neighbour fill, model fill or semantic guess may repair authority-critical fields.

Non-authority exploratory research may use imputation only in a separate research namespace with explicit labels; never product runtime.

### 8. Extractable Primitives dictionary

Decision: `ACCEPT_WITH_NAMING_CORRECTION`
Priority: P1

High reuse value.

Do not map raw variables directly to philosophical prose. Use three layers:

```text
provider_raw_field
-> canonical semantic field
-> extractable primitive
```

Example:

```text
raw: start_x, start_y, end_x, end_y
canonical: event_start_x_m, event_start_y_m, event_end_x_m, event_end_y_m
primitive: displacement_distance_m
```

`centroid_distance` is eligible only when centroid membership and coordinate surfaces are explicit.

`inner_corridor` must be a declared zone taxonomy, not an intuitive label.

Required fields:

```text
primitive_id
definition
formula
required_inputs
units
valid_domain
failure_conditions
claim_ceiling
consumer_modules
```

### 9. X match micro/mezzo/macro analysis from donor data

Decision: `REJECT_AS_WRITTEN / ADAPT_AS_RUNTIME_PRODUCT`
Priority: after ACTIVE_MATCH integration

Donor repos cannot supply match truth.

Correct path:

```text
ACTIVE_MATCH runtime data
-> micro observations
-> mezzo relations / windows
-> macro surface summaries
```

No interpretation is unrealistic because selection and grouping already encode analytical judgment. Correct output is `observation-only, claim-limited`, not interpretation-free.

### 10. Donor data as Fact and mandatory Fix

Decision: `REJECT`

Violations:

```text
donor data is not fact
Faultline does not justify a definitive action
analysis cannot automatically write a coaching fix as truth
```

Adaptable concept:

```text
Fact candidate
Frame
Finding candidate
Faultline candidate
Option set
Follow-up evidence request
```

Replace `Fix` with:

```text
intervention_option_candidate
tradeoffs
required_validation
withdrawal_condition
```

### 11. Scout Report with falsification and counter-scenario

Decision: `ACCEPT_WITH_RUNTIME_AND_SOURCE_BOUNDARY`
Priority: P2

Excellent claim-safety pattern.

Required for every strong player-profile inference:

```text
evidence refs
comparison population
context window
counter-scenario
falsification condition
missing evidence
confidence/eligibility state
```

Donor repos may provide method/templates, not player fact. Player data must come from authorized uploaded/runtime sources.

### 12. Team ontology plus socioeconomic OSINT

Decision: `ADAPT_STRONGLY`
Priority: research lane, not core runtime

Event/context data may support a team-behaviour ontology candidate.

Socioeconomic OSINT may appear only as:

```text
REFERENCE_ONLY_SOCIOCULTURAL_CONTEXT
```

It cannot explain tactics causally without separate evidence.

Required separation:

```text
football evidence block
sociological reference block
hypothesis boundary
no causal bridge by default
```

### 13. Cognitive Load Management / High-Value summary

Decision: `ACCEPT`
Priority: P1/P2

This should become a reusable `analyst_attention_router`.

Selection criteria:

```text
decision relevance
evidence strength
counter-evidence importance
novelty relative to baseline
materiality
claim safety
```

Never remove contradictory evidence merely to simplify the summary.

### 14. Chiaroscuro heatmaps with black/white certainty

Decision: `REJECT_AS_WRITTEN / ADAPT_VISUALLY`
Priority: P3

Caravaggio-inspired contrast is acceptable as visual style.

Black/white analytical certainty is not acceptable because event surfaces contain uncertainty, missingness and sampling effects.

Correct visual contract:

```text
high contrast
explicit no-data mask
uncertainty legend
sample-density annotation
candidate-only title
```

No visual should imply more certainty than the data supports.

### 15. Broadcast Script

Decision: `ACCEPT_WITH_CLAIM_GATE`
Priority: P3 after report pipeline and ACTIVE_MATCH proof

Broadcast output is a consumer, not an authority layer.

Required source chain:

```text
canonical candidate
-> claim gate
-> analyst report block
-> broadcast compression
```

Every compressed line must retain evidence and qualification metadata internally.

### 16. Simulation-based Coach Brief

Decision: `DEFER / ADAPT`
Priority: research after calibrated uncertainty stack

Eligible only as probabilistic scenario generation, not prediction truth.

Required:

```text
assumption registry
prior source
simulation model version
calibration evidence
uncertainty interval
out-of-distribution warning
counter-scenarios
no-action option
```

ConnectionError or missing input blocks simulation promotion.

### 17. Automatic academic literature scan for anomaly

Decision: `ACCEPT_AS_RESEARCH_SUPPORT`
Priority: P2/P3

Literature cannot explain a match anomaly automatically.

Correct architecture:

```text
anomaly candidate
-> research query builder
-> academic/practitioner reference packet
-> analyst review
```

References may suggest competing mechanisms, not validate match truth.

### 18. OSINT pre-match integration

Decision: `ACCEPT_WITH_SOURCE ISOLATION`
Priority: P2

Use separate source families:

```text
official competition/team sources
reputable news
weather authority
injury/suspension sources
market/media context
```

Never fuse OSINT directly into event truth.

Output layers:

```text
verified current facts
reported but unverified items
context candidates
unknowns
```

### 19. Pass-network entropy and topology

Decision: `ACCEPT_WITH_EVENT-ONLY LIMITS`
Priority: P2 after canonical actor/team binding

Scientific basis is sound for graph diagnostics.

Eligible primitives:

```text
pass edge counts
node degree
edge density
component structure
categorical entropy
transition entropy
```

Shannon entropy:

```text
H = - sum_i p_i log(p_i)
```

Claim boundary:

```text
network distribution diagnostic
not spatial control
not off-ball structure
not tactical intention
```

`player area parcelization` is rejected without tracking; event coordinate partitions may only be called event-action concentration zones.

### 20. Mandatory aphorism after every analysis

Decision: `REJECT_AS_MANDATORY / ACCEPT_AS_OPTIONAL EDITORIAL LAYER`
Priority: low

Philosophical statements must not become required product output because they add noise, copyright risk, tone inconsistency and no analytical evidence.

Optional rule:

```text
editorial_epigraph_allowed=true
source verified
short quotation or paraphrase
separate from evidence output
```

## Accepted portfolio

### P0 — Build now

```text
read-only connector permission architecture
reference isolation protocol
connection failure / unknown protocol
no-imputation gate
path and authority protection
PR dependency compatibility contract
```

### P1 — Build next

```text
immutable donor manifest
ERR-101 capability mismatch gate
content-aware event-only eligibility gate
extractable primitive registry
analyst attention router
```

### P2 — After integration spine

```text
claim-safe scout report contract
OSINT pre-match reference adapter
research query builder
pass-network entropy diagnostics
```

### P3 — After ACTIVE_MATCH evidence

```text
broadcast consumer
probabilistic coach brief research candidate
high-contrast uncertainty-aware visual layer
```

## Rejected ideas

```text
donor data as fact
tracking/video packages entering event-only product
silent imputation
prediction during connection failure
mandatory definitive coaching fixes
binary analytical certainty
socioeconomic causal inference from event data
player-space parcelization from pass events
mandatory aphorisms in analytical output
```

## Better architecture

```text
DONOR DISCOVERY PLANE
  read-only connectors
  provenance manifests
  immutable hashes
  timeout state

REFERENCE PLANE
  references/donor_data
  quarantine
  event-only eligibility
  no authority promotion

ADAPTATION PLANE
  capability comparison
  mismatch gate
  primitive mapping
  HPFA-native contract

PRODUCT PLANE
  canonical schema
  dependency CI
  runtime authority
  claim gate
  analysis candidates

CONSUMER PLANE
  analyst report
  scout report
  pre-match packet
  broadcast script
  visual output
```

## Migration plan

```text
M0 policy and path contracts
M1 read-only connector manifest prototype
M2 failure and isolation gates
M3 primitive/dependency registries
M4 end-to-end reference-to-adaptation fixture
M5 ACTIVE_MATCH-only analytical consumers
```

## Tests required

```text
test_donor_credentials_cannot_write_hpfa
test_hpfa_credentials_not_available_to_donor_workflow
test_reference_path_cannot_modify_authority_registry
test_symlink_cannot_bypass_reference_isolation
test_tracking_payload_rejected
test_video_payload_rejected
test_extension_spoof_rejected
test_connection_error_blocks_prediction
test_timeout_emits_unknown_protocol
test_fusion_mismatch_emits_err_101
test_no_imputation_on_required_fields
test_dependency_conflict_blocks_pr
test_primitive_mapping_requires_definition_formula_units
test_osint_does_not_become_event_truth
test_visual_no_data_mask_present
test_no_sample_match_identity_leak
```

## Release readiness

```text
architecture review: POLICY_CORRECTION_PASS
connector runtime: SPEC_ONLY
GitHub Action scripts: NOT_IMPLEMENTED
ACTIVE_MATCH evidence: NONE
production release: NOT_READY
```

## Final founder decision

The first product slice is not a 20-feature suite.

It is:

```text
Read-only Donor Reference Intake + Isolation + Fail-Closed Governance Pack V1
```

This slice unlocks later diversity without allowing donors to contaminate product authority.
