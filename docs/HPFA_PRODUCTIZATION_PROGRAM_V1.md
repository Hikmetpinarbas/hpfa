# HPFA Productization Program V1

## Coordinator Decision

HPFA is no longer managed as raw files or raw capability rows.

The operating chain is now:

```text
Capability Family
→ Composite Apparatus
→ Product Module
→ Product Release
→ Professional Football Intelligence
```

## Current Release

```text
POSTMATCH_RELEASE_0.1
```

## Current Evidence

`hpfa_product_module_registry_v1` is PASS.

Evidence:

```text
line_count: 65
byte_size: 47874
sha256: a6a8bacb194c9dffaae49b8a4bdf1594449e982539649631b469b69f46fcb75b
```

## Current Product Module Registry State

Release scope summary:

```text
RELEASE_0_1_REVIEW_CANDIDATE: 8
RELEASE_0_1_BLOCKED: 7
RELEASE_0_1_READY_CANDIDATE: 6
RELEASE_0_1_SUPPORT: 3
RELEASE_0_2_OR_LATER: 40
```

Blocked Release 0.1 modules currently include:

```text
EVIDENCE_ENGINE / active_match_evidence
CLAIM_ENGINE / claim_confidence_gate
PROGRESSION_ENGINE / progression_consequence
ACTIVE_MATCH_RUNTIME / active_match
REPORT_ENGINE / report_render
AUDIT_ENGINE / metric_registry
CONSEQUENCE_ENGINE / production_waste
```

## Product Backlog Rule

From this point, work is managed by product module backlog, not file backlog.

Each product module must expose:

```text
current_release
sprint
product_module
included_capabilities
module_status_pct
execution_status
claim_boundary
remaining_work
blockers
next_capability
next_action
release_decision
```

## Sprint Rule

Each sprint completes one product module before moving to another.

A product module cannot enter release unless it has ACTIVE_MATCH execution proof or a documented non-runtime support role.

## Policy Externalization

Hardcoded policy must be externalized as candidate policy artefacts first:

```text
release_policy_v1.json
review_policy_v1.json
family_policy_v1.json
external_source_policy_v1.json
```

These are candidate policy files until reviewed. They must not be treated as production registry writes.

## Immediate Next Node

```text
hpfa_postmatch_release_0_1_product_backlog_v1
```

## Purpose

Convert the product module registry into a release backlog for POSTMATCH_RELEASE_0.1.

## Strict Rules

- Do not manage HPFA as files.
- Do not select raw scripts as product modules.
- Do not build composites before module backlog review.
- Do not use Drive or Dropbox as runtime authority.
- Do not bypass claim boundaries.
- Do not bind blocked rows.
- Do not move, delete, rewrite, or production-bind in backlog nodes.
