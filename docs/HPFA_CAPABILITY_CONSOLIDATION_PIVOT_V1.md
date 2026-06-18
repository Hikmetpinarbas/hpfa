# HPFA Capability Consolidation Pivot V1

## Coordinator Decision

The project has passed simple asset discovery.

The next operating model is capability-family based engineering.

## Problem With Asset Inventory Alone

A file inventory is useful, but it does not describe the machine.

Many files are variants of one behavior-producing capability. For example:

```text
progression_v1.py
progression_v2.py
progression_clean.py
progression_runtime.py
progression_builder.py
progression_seed.py
```

These are not six separate product assets. They are one capability family.

## New Management Chain

```text
File
→ Capability Family
→ Composite Apparatus
→ Runtime Execution
→ Football Value
→ Product Module
→ Product Release
→ Professional Football Intelligence
```

## Current Node

```text
hpfa_capability_consolidation_inventory_v1
```

## Mission

Group P0/P1 postmatch candidates into capability families and identify:

```text
variant_count
best_runtime_candidate
composite_exists
execution_exists
claim_safe_signal
report_consumer_signal
current_maturity
action
provenance
```

## Output Principle

The main output is no longer a list of files.

The main output is a capability-family table.

## Required Output Columns

```text
capability_family
variant_count
file_count
directory_count
runtime_count
builder_count
seed_count
legacy_count
review_count
bind_to_core_count
merge_to_composite_count
execution_exists
claim_safe_signal
report_consumer_signal
best_runtime_candidate
composite_exists
current_maturity
product_module
release_target
action
provenance_paths
```

## Product Release Logic

HPFA must be managed as:

```text
Capability
→ Composite
→ Release
```

Initial product target:

```text
POSTMATCH_RELEASE_0.1
```

## Strict Rules

- Do not return to generic asset discovery.
- Do not treat every file as a separate capability.
- Do not call thousands of files canonical code candidates.
- Do not bind until capability family is reviewed.
- Do not delete variants until composite execution is proven.
- Preserve provenance for every composite candidate.

## Next Node

```text
hpfa_capability_consolidation_inventory_v1
```
