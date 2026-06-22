# HPFA Composite Integration Office V1

Lifecycle: COMPOSITE_CANDIDATE  
Status: SCAFFOLD_NOT_PRODUCTION_BOUND  
Runtime authority: ACTIVE_MATCH validation only  
Claim layer: CLOSED  
Report language: CLOSED

## Purpose

This module normalizes intake records from GitHub, Google Drive, Dropbox, Sider Scholar and Termux into one Composite Registry.

It treats every external item as intake evidence only. No intake source becomes runtime truth.

## Product meaning

This module is the donor-control desk. It groups related discoveries into composite candidates and preserves source lineage.

## V1 processing chain

```text
Source Intake
Discovery Fingerprint
Duplicate Merge
Capability Family
Composite Candidate
Boundary Analysis
HPFA Adaptation Candidate
ACTIVE_MATCH Validation Required
```

## V1 scope

Allowed:

```text
source intake normalization
fingerprint generation
duplicate merge by fingerprint
capability family grouping
composite candidate registry
```

Blocked:

```text
event truth assignment
football tactical truth
claim language
report language
production binding
```

## Phone output rule

If this module is executed from Termux and writes user-visible files, write directly into:

```text
/sdcard/Download/HPFA
```

No nested phone output folders.
