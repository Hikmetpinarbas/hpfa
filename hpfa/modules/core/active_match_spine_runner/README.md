# HPFA ACTIVE_MATCH Spine Runner V1

Lifecycle: EVIDENCE_RUNNER_CANDIDATE  
Status: NOT_PRODUCTION_BOUND  
Runtime authority: ACTIVE_MATCH folder only  
Claim layer: CLOSED  
Report language: CLOSED

## Purpose

This module runs a repeatable spine check against a selected ACTIVE_MATCH folder.

It does not produce a football report. It produces evidence about which current HPFA core components can run safely.

## V1 steps

```text
1. Build ACTIVE_MATCH surface manifest
2. Optionally run boundary scorer when a composite registry is provided
3. Write one JSON evidence file
4. Write one TXT summary file
```

## Phone output rule

When used from Termux, all user-visible outputs must be written directly to:

```text
/sdcard/Download/HPFA
```

No nested phone output folders.

## Boundary

Blocked:

```text
football claim
report language
production binding
runtime truth assignment beyond ACTIVE_MATCH surface validation
```

Allowed:

```text
surface manifest evidence
candidate scoring evidence
flat summary output
```
