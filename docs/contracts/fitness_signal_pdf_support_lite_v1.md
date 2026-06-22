# HPFA Fitness Signal PDF Support Lite V1 Contract

Date: 2026-06-22

Status: SUPPORT_CONTRACT_SPEC

## Product Node

```text
Fitness Signal PDF Support Lite V1
```

## Purpose

Detect, index and isolate fitness/load/GPS/HRV/wellness/RPE PDF files that are present inside the ACTIVE_MATCH folder.

This support node exists because the operator reported that fitness PDF files are present inside the same Termux ACTIVE_MATCH test match folder.

## Source Authority

If PDFs are physically present inside:

```text
runtime/active_single_match/current
```

they may be indexed as ACTIVE_MATCH-adjacent support documents.

They are still not event truth.

## Claim Boundary

Fitness PDF support may produce:

- PDF file presence evidence
- file name inventory
- file size evidence
- modified-time evidence if available
- extraction status
- detected text snippets only if extraction is implemented
- support-signal availability flag

Fitness PDF support must not produce:

- fatigue truth
- load truth
- injury truth
- tactical truth
- dominance truth
- player physical state truth
- event truth override
- ACTIVE_MATCH event correction

## Required Status Language

Allowed statuses:

```text
PDF_PRESENT_EXTRACTION_PENDING
PDF_INDEX_PASS
PDF_EXTRACTION_PASS
PDF_EXTRACTION_FAIL_CLOSED
SUPPORT_SIGNAL_AVAILABLE_NOT_RUNTIME_EVENT_TRUTH
```

## Inputs

Required:

- `active_match_dir`
- `--out-dir`

Allowed output roots:

```text
/sdcard/Download/HPFA
/storage/emulated/0/Download/HPFA
```

Nested phone output directories must be rejected.

## Outputs

```text
fitness_signal_pdf_index_v1.json
fitness_signal_pdf_index_v1.txt
```

Flat phone output only.

## Index Fields

Each indexed PDF row should contain:

- source_file
- relative_path
- size_bytes
- source_role
- support_signal_type
- runtime_event_truth
- extraction_status
- claim_boundary

## Extraction Policy

Initial Lite version may index file presence without text extraction.

If text extraction is added later, the output must include:

- extraction method
- extraction errors
- extracted text length
- table detection flag if possible
- no medical/fitness conclusion without analyst review

## Relationship to P2

P2 Canonical Event Lite remains event surface normalization.

Fitness Signal PDF Support Lite is parallel support. It cannot change:

- canonical_lite_row_count
- canonical_event_count
- event_family_volume
- zone/channel distribution

## Acceptance Criteria

The support node can reach ACTIVE_MATCH_EVIDENCE_PASS only if:

1. module compiles;
2. tests pass;
3. ACTIVE_MATCH run indexes PDF files if present;
4. flat phone outputs are written;
5. no fatigue/load/tactical claim is emitted;
6. PDF files are clearly marked as support signal, not event truth.

## Current Status

```text
SUPPORT_CONTRACT_SPEC_WRITTEN
IMPLEMENTATION_NOT_STARTED
ACTIVE_MATCH_EXECUTION_NOT_RUN
```
