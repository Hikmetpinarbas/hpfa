# Full Data Reading and Meaning Spine Note V1

Status: DIRECTIONAL_NOTE / REVIEW_REQUIRED

Linked PR: #92

## Purpose

This note records the long-term product objective without changing the current work order.

HPFA should become a system that can read and interpret all available match data surfaces, not only generate report text from selected metrics.

## Core Objective

The target system must be able to read every available source surface:

- CSV
- XML
- XLSX
- PDF
- TXT / methodology notes
- donor registry material
- runtime manifests
- future video/tracking support surfaces when available

Then it must decompose every usable row and column into evidence objects before recombining them into analyst-facing football meaning.

## Work Order Must Not Change

This note does not move P2I ahead of R1 or P2C.

Current order remains:

1. R1 permission spine closure
2. P2C Event-Time-Space Binder
3. P2H Postmatch Report Skeleton
4. P2I Ontology Chain
5. Claim Eligibility Gate
6. Football Output Audit
7. Analyst-facing execution

## Meaning Spine

The future full-data comprehension spine should follow this route:

```text
source surface
-> row/column inventory
-> source role map
-> ingestion audit
-> field semantic mapping
-> event-time-space atom
-> evidence object
-> context/window object
-> sequence or pattern candidate
-> value/consequence proxy
-> player-role surface
-> opponent correspondence
-> ontology candidate
-> style candidate
-> claim gate
-> football output audit
-> analyst meaning
```

## Required Principle

Every row and every column must be treated as a potential evidence surface, but no row or column becomes football truth by itself.

Allowed:

- surface evidence
- field-level evidence
- row-level evidence
- evidence object
- candidate signal
- diagnostic meaning
- proxy meaning
- gated analyst judgement

Blocked:

- canonical event count from raw rows
- tactical truth from one table
- player quality truth from one metric
- style truth from one match
- dominance or control claim without explicit gates
- video/tracking claim without video/tracking support

## Product Consequence

Future modules should optimize for these capabilities:

1. read all available data surfaces
2. preserve source role and authority
3. map fields semantically
4. preserve unmapped fields
5. expose missing columns
6. detect source conflict
7. build evidence objects
8. attach counter-scenarios
9. route claims through gates
10. render analyst meaning only after audit

## Status

DIRECTIONAL_NOTE / REVIEW_REQUIRED.

No production release claim.
