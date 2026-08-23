# HPFA Open PR Capability Classification — 2026-08-23

Status: `C0A_AUTHORITY_AND_PR_CLASSIFICATION_CLOSED / C0B_FILE_LINEAGE_NEXT / NOT_PRODUCTION / NOT_MERGED`

## Purpose

This record classifies the 79 open pull requests observed in `Hikmetpinarbas/hpfa` so open PR existence can no longer be mistaken for product authority, current capability authority, ACTIVE_MATCH truth, merge readiness or production release.

The classification is a consolidation routing aid. It does not authorize chronological merging.

## Current authority split

```text
PRODUCT_MAIN
  main
  snapshot_head=105539970ffd0ca8b5d592a68e800da6057e3274

CURRENT_DEVELOPMENT_FRONTIER
  PR #278
  head=33ebcc161576e0e11012cc8f3c221512013c77f2

CURRENT_CONSOLIDATION_CONTROL
  PR #268
  branch=integration/current-spine-consolidation-preflight-v1
  head=LIVE_REF_REQUIRED

SOLE_ACTIVE_MATCH_RUNTIME_AUTHORITY
  runtime/active_single_match/current
```

No Google Drive, Dropbox, PDF, external audit, donor repo, academic paper, app/agent output or historical runtime bundle may override the ACTIVE_MATCH runtime authority.

## Classification

### 1. SPEC_REFERENCE_BACKLOG — 11 PRs

```text
#39 #49 #79 #86 #90 #92 #94 #104 #105 #106 #107
```

Role:
- specification/reference backlog;
- donor or planning value may remain;
- not executable current authority;
- not merge-train input.

### 2. SUPERSEDED_HISTORICAL_IMPLEMENTATION — 27 PRs

```text
#155 #157 #158 #159 #161
#164 #166 #170 #171 #172 #175 #177 #178 #181 #183 #185
#188 #190 #192 #194 #196
#199 #201 #203 #205 #206 #207
```

Role:
- historical implementation/donor surface;
- do not merge chronologically;
- recover only reviewed behaviour, tests, contracts or invariants needed by the final current snapshot;
- use `ADAPT_NOT_COPY`.

### 3. CURRENT_CORRECTION_EXTRACTION_SOURCE — 5 PRs

```text
#180 #228 #232 #234 #243
```

Role:
- contains a correction or quality behaviour that may belong in a final snapshot;
- exact file-lineage audit is required before extraction;
- PR itself is not automatically a landing unit.

### 4. DEFERRED_SIDE_CAPABILITY — 8 PRs

```text
#198 #218 #219 #223 #237 #239 #241 #258
```

Role:
- potentially valuable capability;
- outside the current P0 consolidation spine;
- preserve for post-consolidation decision;
- do not reopen feature expansion during feature freeze.

### 5. SUPERSEDED_CONSOLIDATION_CONTROL — 2 PRs

```text
#245 #247
```

Role:
- prior authority/consolidation attempts;
- useful historical planning evidence only;
- current control authority is PR #268.

### 6. CURRENT_FRONTIER_STACK — 25 PRs

```text
#248 #249 #250 #251 #253 #254 #256
#259 #260 #261 #262 #263 #264 #265 #266 #267
#270 #271 #272 #273 #274 #275 #276 #277 #278
```

Role:
- current capability source surface for `FINAL_CAPABILITY_SNAPSHOT` extraction;
- still `NOT_MERGED` and `NOT_PRODUCTION`;
- current exact code/file lineage must win over PR chronology;
- corrections must be folded into the capability layer they repair.

Sub-spines:

```text
Foundation / source authority sources
  #248 #249 #250 #251 #253 #254 #256

Evidence Spine
  #254 → #259 → #260 → #261 → #262 → #263

Football Reconstruction
  #264 → #265 → #266 → #267

Intelligence correctness hardening
  #270 → #271 → #272 → #273 → #274 → #275 → #276 → #277 → #278
```

### 7. CURRENT_CONSOLIDATION_CONTROL — 1 PR

```text
#268
```

Role:
- current consolidation governance/control surface;
- does not itself create match truth or production runtime capability;
- hosts C0 authority normalization and subsequent consolidation records.

## Landing rule

The landing unit remains:

```text
FINAL_CAPABILITY_SNAPSHOT
```

Forbidden:

```text
historical PR merge train
giant merge
blind full-stack rebase
stale runtime evidence promoted to current evidence
external audit promoted to repository authority
parallel replacement engine when current producer can be safely extended
```

## C0 progress

Completed in this slice:

```text
authority surfaces normalized=true
open PR count classified=79/79
classification coverage complete=true
```

Still required before C0 is fully closed:

```text
C0B = exact final-state file lineage map
```

C0B must answer, per landing capability:

1. Which current file is the final producer/contract/test/workflow/runner file?
2. Which historical PR/file is superseded?
3. Which correction PR contributes a behaviour that must be folded in?
4. Which files are donor/reference only?
5. What is the exact extraction source for the final capability snapshot?

## Global locks

```text
feature_freeze=true
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
merge_requires_explicit_user_approval=true
```

No merge, release, auto-merge or production binding is authorized by this record.
