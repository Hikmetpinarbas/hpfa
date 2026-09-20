# HPFA — NEW OPERATOR HANDOFF — 2026-09-20

Record role: NEW_OPERATOR_SNAPSHOT  
Canonical current handoff: `docs/governance/HPFA_OPERATOR_HANDOFF_CURRENT.md`  
Product: **Hikmet Pınarbaş Football Analytics**

## 0. START HERE

Do not ask the user to reconstruct project history.

Mandatory startup:
1. Read `docs/governance/HPFA_MASTER_PROJECT_DIRECTIVE_SHORT_CURRENT.md`.
2. Read `docs/governance/HPFA_OPERATOR_HANDOFF_CURRENT.md`.
3. Read this snapshot.
4. Fresh-fetch PR #364 and the Termux worktree before every write/current-state claim.
5. Verify ACTIVE_MATCH physically before runtime claims.
6. Do not merge/release/force-push/reset/rebase destructively without explicit user approval.

## 1. CORE PRODUCT LAW

HPFA = Hikmet Pınarbaş Football Analytics.

`EVENT ⊂ ZFGV` and `ZFGV != EVENT`.

Evidence spine:

`SOURCE → SURFACE → OBSERVATION → SEMANTICS → IDENTITY/DEPENDENCY → TIME/SPACE ADMISSION → RELATION → EPISODE/PROCESS → FEATURE → METRIC/MODEL → SIGNAL → HYPOTHESIS → COUNTEREVIDENCE → FINDING → CLAIM → ANALYST OUTPUT`

Every task asks:

> Which real gap does this close, and what new defensible football knowledge does it give the analyst?

No clear gain → `LATER / REJECT`.

Operating laws:
- WIP=1
- no parallel engine
- REHABILITATE_BEFORE_PARALLEL_ENGINE
- ADAPT_NOT_COPY
- CODE LAST
- PASS != RELEASE
- CI PASS != ACTIVE_MATCH
- ACTIVE_MATCH != production
- donor PASS != product PASS

## 2. TRUTH LOCKS

- ROW != EVENT TRUTH
- EVENT != WHOLE OBSERVATION UNIVERSE
- PROVIDER LABEL != PHYSICAL/TACTICAL TRUTH
- AGGREGATE != ACTION IDENTITY
- MULTIFORMAT != INDEPENDENT EVIDENCE
- SAME TIMESTAMP != TOTAL ORDER
- COORDINATE != TRACKING
- PROCESS LABEL != COACH INTENTION
- RECURRENCE != CAUSALITY
- MODEL OUTPUT != FACT
- LLM TEXT != EVIDENCE
- ABSENCE != COUNTEREVIDENCE
- NO_VISIBLE_FOLLOWUP != FAILURE

C02 locks:
- OUTCOME MUST NOT DEFINE ITS OWN ELIGIBLE DENOMINATOR
- MINIMUM SUPPORT THRESHOLD != EVIDENCE STRENGTH TRUTH
- SHRUNK RATE != OBSERVED RATE
- NO P-VALUE != NO MULTIPLICITY RISK
- RANKED EXTREME != STABLE SIGNAL
- EXACT COMPUTATION != VALID FOOTBALL INFERENCE
- CLUSTER-AWARE != ASSUMPTION-FREE

Without tracking/video do not claim true shape, compactness, pitch control, off-ball geometry, true speed/load, pressure geometry, coach intention, dominance or causality.

## 3. CURRENT FRONTIER SNAPSHOT

Repo: `Hikmetpinarbas/hpfa`  
PR: `#364`  
Branch: `repair/post-sequence-current-ledger-v1`  
Snapshot head at handoff creation: `239d9a18f5dc95984caf3cc84b5e37b1d0f253fb`  
State at handoff creation: `OPEN / DRAFT / UNMERGED / NOT_PRODUCTION`

This SHA is a handoff snapshot, not permanent authority. Re-fetch before use.

Current product direction:

`MECHANISM CANDIDATE → SAFE FOOTBALL FINDING COMPOSITION → HUMAN ANALYST OUTPUT`

Recent commits:
- `239d9a18` Block outcome leakage in comparison contracts
- `fd43b301` Refresh operator authority and repository reaudit
- `58168f46` Polish bilingual analyst report language
- `7f998955` Expand bilingual reports into football language
- `d28c00e5` Close portable test and XLSX projection coverage debt
- `2f23ceba` Tighten C02 descriptive association semantics
- `145c5747` Bind provider cues to rendered mechanism records

PR #359 is historical/base support, not current interactive WIP.

## 4. CI / TEST STATE

At snapshot head `239d9a18...`, all 9 current GitHub workflows were SUCCESS:
- Core Pipeline Orchestrator Lite V1
- C1 Foundation Final Snapshot V1
- C2 Evidence Spine Final Snapshot V1
- C3 Reconstruction Final Snapshot V1
- C4 Intelligence Final Snapshot V1
- ACTIVE_MATCH Full Spine V1
- Aggregate Definition Alignment Lite V1
- Capability Closure Guard Lite V1
- Full Repo Health Audit V1

Latest comprehensive local product-core audit before later language/outcome-leakage commits:
- 72 / 72 core modules have tests
- 1898 pytest cases
- 0 failures
- 0 errors
- product core PASS
- whole tree REVIEW_REQUIRED because legacy/vendor/release-convergence remain separate concerns

YelFootballLab physical donor suite:
- 185 tests PASS

## 5. LAST PHYSICAL ACTIVE_MATCH

Last physically verified exact head:
`7f99895506c134d8a29cf398b41f9776b90211d4`

Output:
`$HOME/hpfa_operator/physical_7f998955_reaudit`

Verification:
- exact_product_commit_verified=true
- status=REVIEW_REQUIRED
- decision=EXACT_HEAD_ACTIVE_MATCH_EVIDENCE_SURFACE_EVALUATED

Safe Finding:
- ABSTAIN=0
- DOWNGRADE=79
- EMIT=0

The physical report currently contains Trabzonspor / Galatasaray team surfaces.

Do not transfer this physical evidence to current head `239d9a18...`.

Current-head physical ACTIVE_MATCH acceptance is still required because later commits changed report language, authority state and comparison outcome-leakage guards.

## 6. C02 STATE

C02 = player/dyad × visible shot-linked association.

No new significance engine. Do not implement Fisher/permutation/bootstrap/shrinkage merely because a table can be formed.

C02 claim ceiling:
`MATCH_LOCAL_VISIBLE_ASSOCIATION_ONLY`

C02 is connected to governed composition but:
- creates no independent support
- absence is not counterevidence
- unresolved is not resolved negative
- no causal player credit
- no statistical significance
- no stable signal
- no forced EMIT

## 7. SAFE FINDING STATE

0 EMIT is valid.

Do not optimize toward EMIT count.

Professional finding still needs enough dependency control, support spread, counterevidence scope, context scope, consequence resolution, unresolved burden handling and selection-risk visibility.

Goal:
**information compression without truth loss**.

## 8. BILINGUAL ANALYST OUTPUT

Surfaces:
- `HPFA_ANALYST_REPORT.txt` = technical/audit
- `HPFA_ANALYST_REPORT_TR.txt` = Turkish football-analyst report
- `HPFA_ANALYST_REPORT_EN.txt` = English football-analysis report

Current TR/EN report includes:
1. visible team process profile
2. player/pair × attack-outcome review
3. mechanism candidates for analyst review
4. claim boundary

Internal tokens must not leak into the main football sentence.

Do not tell the user:
- admitted positional-attack family
- eligible unit
- visible annotation
- occurrence-disjoint cluster
- post-hoc rank
- claim ceiling

Those belong in evidence metadata only.

### Physical language review

The 7f998955 Turkish report improved substantially but still has product-language debt:
- raw display labels such as `galatasaray (29205)` / `trabzonspor (77018)`
- phrases such as `230 adaylık tarama` are too research-like for the main football report
- `mekanizma adayı` should become a natural football description where safely nameable
- C02 sentences remain somewhat repetitive/mechanical
- report still does not reconstruct the match into a strong 3–5 mechanism story
- evidence notes must remain inspectable but secondary to football meaning

Improve presentation; do not delete evidence.

## 9. REPOSITORY RE-AUDIT

Canonical record:
`docs/governance/HPFA_FULL_REPOSITORY_REAUDIT_2026-09-20.md`

### RELEASE_CONVERGENCE_DEBT
`origin/main` and current ZFGV development history do not form one simple natural ancestry chain. Older PRs are often disconnected/diverged.

Do not force-push, destructive-rebase, reset-to-main or blind-merge.

Open PR list != current product backlog.

A user-approved convergence/release plan will eventually be required.

### TECHNICAL DEBT CLOSED
- Termux executable test was incorrectly requiring group/other execute bits; fixed to current-user executability.
- `xlsx_entity_metric_row_projection_lite` was the only core module without tests; tests added.

### HYGIENE / AUTHORITY DEBT
Tracked repo still contains legacy `hpfa-main/`, vendor trees, compatibility wrappers, historical generated `out/` surfaces and runtime-evidence snapshots.

Presence != runtime authority.

Do not delete by file count. Classify reachability and authority first.

### PACKAGING MATURITY DEBT
`pyproject.toml` is old/minimal and is not a reliable description of the whole current runtime surface.

Do not blindly add dependencies. Current XLSX product reading is intentionally native/stdlib-oriented; `openpyxl` is mainly test/tool fixture support in the current path.

### SECURITY
Reviewed non-donor product surface showed no obvious committed credential-pattern hit.

## 10. YEL FOOTBALL LAB

Repo:
`Hikmetpinarbas/YelFootballLab`

Role:
DONOR / LAB ONLY.

Physical suite:
185 tests PASS.

Useful idea already adapted:
`finding → natural football narrative → counterevidence → limitation`

Do not copy Yel architecture or loosen HPFA contracts.

Donor decisions:
- ALREADY_ABSORBED
- ADAPT_NOW
- ADAPT_LATER
- TEST_OR_CONTRACT_DONOR
- REJECT_HISTORICAL

Only ADAPT_NOW when a proven current-owner gap exists.

## 11. POST-LOSS REGAIN RESEARCH

Do not open a parallel WIP.

Useful research capital:
- loss-normalized regain incidence
- 0–5 / 5–10 grouped timing
- territory
- recovery height
- pressing context
- player/role concentration
- consequence after regain
- counterevidence when regain fails

Locks:
- REGAIN != COUNTERPRESS TRUTH
- FAST REGAIN != PRESSING QUALITY
- RECOVERY LOCATION != CAUSAL PRESS MECHANISM

Survival/hazard/competing risks/xR10:
`RESEARCH_REQUIRED`

Tracking-dependent pressure geometry:
`UNOBSERVABLE_WITH_CURRENT_DATA`

## 12. NEXT OPERATOR — FIRST ACTIONS

1. Fresh-verify PR #364 and Termux worktree.
2. Confirm current head/remote clean.
3. Run exact-current-head ACTIVE_MATCH physical acceptance.
4. Verify Safe Finding counts; no EMIT increase is required.
5. Read TR/EN analyst reports as football products.
6. Red-team football language: remove IDs from primary display names, reduce research jargon, keep evidence note separate, preserve uncertainty.
7. Verify the new outcome-leakage comparison guard physically.
8. If current head physically passes, run one blind second-match exact-head acceptance.
9. Reconcile open PRs/issues semantically against current tree; do not auto-close.
10. Return to the single bottleneck:
   `MECHANISM CANDIDATE → SAFE FOOTBALL FINDING COMPOSITION`

## 13. USER COMMUNICATION

The user is a football analyst, not a software operator.

Do not make the user run terminal commands, locate paths, carry SHA values, debug CI or manage Git branches.

Default report:
1. Ne yaptım?
2. Sorun çözüldü mü?
3. Futbola ne kazandırdı?
4. Şimdi ne yapıyorum?
5. Kullanıcıdan gereken?

Good:
> Aynı hücum biçimi başarılı ve başarısız örneklerde farklı sonuçlara gidiyor. Şimdi bu iki varyantın nerede ayrıştığını inceliyoruz.

Bad:
> Grammar-stable variant family has 33 occurrence-disjoint clusters.

## 14. TOOL ROLES

- GitHub = product/code/PR/test/CI
- Remote Desktop Commander = Termux / physical runtime / ACTIVE_MATCH
- Drive / Dropbox = support/donor/history
- YelFootballLab = donor lab
- Wolfram / Mathbox / Precise Special Functions = mathematical verification, not football truth
- Figma / MobileMockup = analyst UI/presentation
- Vercel = preview only; no production deploy without approval
- academic connectors = scientific validation

## 15. RELEASE LOCK

No merge.
No release.
No production binding.
No destructive history rewrite.

`canonical_event_count=UNKNOWN`  
`true_action_count=UNKNOWN`  
`production_release=false`

Release/convergence requires explicit user approval.

## 16. FIRST MESSAGE TO USER

After reading repo handoff, do not ask for project history.

Say, in substance:

> Devri aldım. Current GitHub head ile Termux fiziksel durumu eşleştiriyorum. Sonra current-head ACTIVE_MATCH kabulünü ve Türkçe/İngilizce raporların futbol dili kontrolünü kapatacağım. Kullanıcıdan şu anda işlem gerekmiyor.

Then work.
