# HPFA OPERATOR HANDOFF — CURRENT

Updated: 2026-08-19 12:10 TRT
Record role: CURRENT_OPERATOR_HANDOFF
Product repo: `Hikmetpinarbas/hpfa`
Runtime authority: `runtime/active_single_match/current`

## 0. NEW OPERATOR — READ THIS FIRST

This file exists so a new operator can continue HPFA without asking the user to reconstruct prior work.

Mandatory startup sequence:
1. Read `docs/governance/HPFA_MASTER_PROJECT_DIRECTIVE_SHORT_CURRENT.md`.
2. Read this file completely.
3. Read the Google Drive document `HPFA ANA REPO — CANLI İŞ TAKİP VE DURUM KAYDI` for the long historical/operator ledger.
4. Re-fetch GitHub current main and current PR heads before any write.
5. Verify `runtime/active_single_match/current` before any ACTIVE_MATCH claim.
6. Historical runtime evidence never transfers automatically to a new head or a new match.
7. Do not ask the user to repeat project history already recorded here unless a material ambiguity remains after verification.

## 1. IMMUTABLE OPERATING RULES

- `hpfa` is the only executable product repo.
- HP-Motor / HP-Engine / HP-PROJELERI are donors only: `ADAPT_NOT_COPY`.
- Google Drive / Dropbox / PDFs / archives / academic sources are `REFERENCE_ONLY` or `DONOR_SUPPORT` and never override ACTIVE_MATCH.
- Runtime truth exists only at `runtime/active_single_match/current`.
- CSV/XML/XLSX visible rows are not canonical events.
- `canonical_event_count=UNKNOWN`.
- `production_release=false`.
- PASS != RELEASE; CI SUCCESS != ACTIVE_MATCH evidence; MERGED != PRODUCTION_RELEASE.
- Same-content reflections must not be double-counted.
- Product code must remain match-agnostic and preserve `test_no_sample_match_identity_leak`.
- No nested phone output directories.
- No merge/release/production decision without explicit user approval.
- External runtime dependencies are disfavoured: HPFA should own deterministic internal implementations where practical. Do not silently introduce external model/API/network dependencies.

## 2. CURRENT ACTIVE_MATCH

Current runtime match:
`Genclerbirligi Ankara 2-1 Fenerbahce — 15.08.2026`

Current visible package: 8 files.
Expected role surfaces after content-based resolution:
- PLAYER: CSV + XML + XLSX = 3
- GOALKEEPER: CSV + XML + XLSX = 3
- TEAM: CSV + XML = 2

All current-match counts must be recomputed from this runtime. Do not reuse old Australia–Turkey / previous-match counts.

## 3. CURRENT OPEN PRODUCT LINEAGE

### PR #256 — Content-Based Source Role Resolution V1
Branch: `work/content-source-role-resolution-v1`
Exact validated head: `ac89fba962ae948d5807d85cb451b2f9813b3724`
State: OPEN / DRAFT / MERGEABLE / NOT_MERGED / NOT_PRODUCTION.

ACTIVE_MATCH exact-head evidence:
- supported files: 8/8
- admitted role files: 8/8
- unresolved roles: 0
- GOALKEEPER_SURFACE_CANDIDATE=3
- PLAYER_SURFACE_CANDIDATE=3
- TEAM_SURFACE_CANDIDATE=2
- hard blocks: 0
- filename support used for admission: false for all 8 files

Safe meaning: filenames are no longer required to decide PLAYER/TEAM/GOALKEEPER candidate roles. This is role-candidate evidence, not validated identity/event truth.

Known non-blocking cleanup: a successfully admitted PLAYER surface can still retain the intermediate reason token `CONTENT_ROLE_EVIDENCE_INSUFFICIENT`; reason-provenance cleanup remains desirable.

### PR #254 — Row Nucleus lineage candidates V1
Branch: `work/reconstruct-row-nucleus-research-hardened-v1`
Head: `2a7084fbb193a3925e1a87cc9691629d0739b031`
State: OPEN / DRAFT / MERGEABLE / NOT_MERGED / NOT_PRODUCTION.

Important: the PR body contains ACTIVE_MATCH evidence from the previous match. Treat that runtime evidence as HISTORICAL MATCH-LOCAL SUPPORT only. Current-match role handling must flow through #256 before fresh downstream revalidation.

### PR #253 — Reflection lineage resolver
Historical same-role CSV/XML serialization-lineage resolver. Existing implementation lineage still contains filename-derived source-role assumptions. It must be adapted to consume central content-based role resolution rather than independently re-infer role from filename.

### PR #258 — Statistical Spatial Evidence Lite V1
Branch: `work/statistical-spatial-evidence-v1`
Base: #256 branch
Exact current head: `1c81a2db668046b05b7071aeaeb82bba58c0092f`
State: OPEN / DRAFT / MERGEABLE / NOT_MERGED / NOT_PRODUCTION.

Engineering:
- Statistical Spatial Evidence CI: SUCCESS
- XLSX Surface Reader CI: SUCCESS
- native XLSX backend: `HPFA_NATIVE_OOXML_V1`
- `openpyxl` runtime dependency removed
- `openpyxl` XLSX-test dependency removed
- self-contained runtime dependency guard PASS

ACTIVE_MATCH exact-head evidence:
- status=REVIEW_REQUIRED
- eligible_coordinate_nucleus_count=7478
- spatial_distribution_candidate_group_count=6
- excluded_review_required_nucleus_count=12
- excluded_missing_coordinate_nucleus_count=0
- excluded_out_of_frame_nucleus_count=0
- excluded_missing_team_candidate_nucleus_count=0
- hard_block_hits=[]
- review_hits=[`upstream_row_nucleus_review_preserved`]

Groups admitted as spatial evidence:
- PLAYER × 2 team candidates
- TEAM × 2 team candidates
- GOALKEEPER × 2 team candidates

Safe analyst meaning: current visible coordinate surfaces separate into two team candidates across all three source-role routes. This is row-nucleus coordinate distribution evidence only. It is not attacking-third truth, team-shape truth, dominance truth, pitch-control truth or tactical truth.

Do not assume the 12 current review nuclei are the same administrative labels observed in the previous match. Audit them on the current ACTIVE_MATCH before classifying them.

## 4. CURRENT ANALYST NORTH STAR — ISSUE #257

Issue #257: `Trackable Action Spine V1 — 8 match surfaces into analyst-usable action traces`.

User requirement:
The 8 files are different surfaces of the same match-action universe, not 8 independent datasets. The product must make a football action traceable across compatible PLAYER / TEAM / GOALKEEPER surfaces while XLSX remains aggregate/support evidence.

Required chain:
`content role → serialization lineage → row nucleus → evidence atom → match-local identity → semantic role → multi-label action bundle → cross-role relation → selected action trace → consequence → sequence → repeated pattern → analyst interpretation`

This is a foundational step, not the final HPFA goal. It exists so later phase, pattern, rhythm, value and analyst reasoning can be built on a reliable action stream.

## 5. CURRENT PRODUCT PRIORITIES

P0 — Preserve current authority and runtime evidence discipline.

P1 — Integrate #256 content-resolved roles downstream:
- remove/neutralize #253 filename-role authority;
- make #253/#254 consume the central role-resolution output;
- preserve role/conflict provenance;
- rerun current ACTIVE_MATCH exact-head evidence.

P2 — Audit the 12 current `REVIEW_REQUIRED` row nuclei from #258. Do not promote or suppress them without current-match evidence.

P3 — Build/reconstruct the Trackable Action Spine using current product first and historical modules as donors:
- Evidence Atom (#188 lineage)
- Match-Local Identity (#190 lineage)
- Semantic Role / Action Bundle (#192 lineage)
- Cross-Role Relation (#196 lineage)
- Selected Action Consequence (#199/#203 lineage)
- Visible Sequence (#205 lineage)
All historical runtime counts are non-authoritative until revalidated on current ACTIVE_MATCH.

P4 — Spatial/statistical layer remains subordinate to the action spine. Existing candidate-safe spatial metrics can be retained, but do not let them bypass action/identity/coordinate gates.

P5 — Later modelling registry after prerequisites: xT/VAEP, consequence value, survival/competing risks, Bayesian shrinkage, hypothesis tests, KDE/Ripley, temporal graphs, changepoints, entropy/process mining, calibrated uncertainty.

## 6. RESEARCH / CLAIM CEILING

Allowed direction: observable event/action chains, regional distributions, consequence, sequence recurrence, candidate pattern evidence, explicit uncertainty/falsifier.

Never promote from event-only data to truth without the missing sensing/evidence:
- pitch control
- off-ball structure
- real team shape/compactness
- body orientation
- coach intention
- fatigue/cognitive state
- true pressure field
- true 22-player geometry
- causal counterfactual percentages without an admitted causal model

Synthetic trajectories / field-flow / advanced physics analogies may be research or visualization candidates only; never observed truth.

## 7. SOURCE SEARCH ORDER BEFORE CODING

1. current `hpfa` producer/current open product PR
2. HP-Motor
3. HP-Engine
4. HP-PROJELERI
5. Google Drive governance/donor library
6. Dropbox archive/donor library
7. academic support
8. Termux discovery/runtime evidence
9. CODE LAST

## 8. HANDOFF CHECKLIST AFTER EVERY MAJOR CHANGE

Update this file and the Drive live tracker with:
- timestamp
- repo main head
- development/current PR exact head
- PR/issue number
- what changed
- Engineering Evidence
- Analyst Evidence
- solved/not solved
- current status
- blocker
- next safe action
- ACTIVE_MATCH required? yes/no
- claim boundary
- merge/release decision

Never overwrite historical evidence as if it were current. Mark superseded/historical states explicitly.

## 9. ONE-LINE TAKEOVER COMMAND FOR A NEW OPERATOR

User can say:
`HPFA_OPERATOR_HANDOFF_CURRENT.md ve Drive'daki HPFA ANA REPO — CANLI İŞ TAKİP VE DURUM KAYDI'nı oku; GitHub current head'leri ve ACTIVE_MATCH'i yeniden doğrula; NEXT SAFE ACTION'dan devam et; benden geçmişi tekrar isteme.`

## 10. CURRENT NEXT SAFE ACTION

1. Verify #256 and #258 exact heads still match this handoff.
2. Inspect the 12 current #258 upstream review nuclei on the current ACTIVE_MATCH.
3. Implement the narrow #256 → #253/#254 role-resolution integration; no filename role authority downstream.
4. Revalidate #253/#254 on current ACTIVE_MATCH.
5. Only then continue Evidence Atom → Trackable Action Spine reconstruction.

Current project status:
`ACTIVE_MATCH_CURRENT_GENCLERBIRLIGI_FENERBAHCE / CONTENT_ROLE_RESOLUTION_ACTIVE_MATCH_PASS / SPATIAL_EVIDENCE_ACTIVE_MATCH_PASS_WITH_UPSTREAM_REVIEW_PRESERVED / TRACKABLE_ACTION_SPINE_NEXT / canonical_event_count=UNKNOWN / production_release=false`
