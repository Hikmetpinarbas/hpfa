# HPFA Reference Document Ingest Lite V1 Contract

Date: 2026-06-22

Status: P2B_CONTRACT_SPEC

## Product Node

```text
P2B Reference Document Ingest Lite V1
```

## Purpose

Index and extract page-level text from PDF reference/support documents located inside an input directory, including ACTIVE_MATCH-adjacent fitness PDFs.

This node adapts donor capability from HP-Motor and HP-Engine but does not copy donor modules as production code.

## Donor Capability

HP-Motor donor support:

- `tools/ingest_reports.py`
  - SHA256 file identity
  - manifest/index pattern
  - archive/source identity pattern

- `tools/extract_report_pages.py`
  - page-level PDF extraction
  - JSONL output
  - chars_total
  - texty_pages
  - err_pages
  - text_based / possibly_image_based classification

HP-Engine donor support:

- `engine/hp_engine_reader.py`
  - generic multi-format file reader
  - PDF text extraction using page-level reader loop
  - TXT/CSV/JSON/XML/XLSX/DOCX/PDF reader concept

Decision:

```text
ADAPT_NOT_COPY
```

## Source Authority

PDF documents are reference/support documents.

They may support:

- vocabulary
- official report reference
- scouting note reference
- fitness/load support availability
- page-level text evidence

They cannot override:

- ACTIVE_MATCH event evidence
- canonical-lite event rows
- row-level football evidence
- claim gate

## Claim Boundary

Allowed:

- PDF file presence evidence
- PDF SHA256 identity
- page-level extracted text evidence
- text-based / possibly image-based classification
- support-signal availability
- extraction audit

Blocked:

- fatigue truth
- load truth
- injury truth
- tactical truth
- dominance truth
- coach intention
- off-ball truth
- event truth override
- possession/phase truth

## Inputs

Required:

```text
--input-dir <directory>
--out-dir <flat output root>
```

Optional:

```text
--active-match-mode
```

If active-match-mode is used, PDFs are marked as ACTIVE_MATCH_ADJACENT_SUPPORT_DOCUMENT, not runtime event truth.

## Outputs

Flat phone output only:

```text
reference_document_manifest_v1.json
reference_document_pages_v1.jsonl
reference_document_extraction_audit_v1.json
reference_document_extraction_audit_v1.txt
```

## Manifest Fields

Each PDF manifest row should include:

- document_id
- source_file
- relative_path
- size_bytes
- sha256
- source_role
- support_signal_type
- runtime_event_truth
- claim_boundary

## Page JSONL Fields

Each page row should include:

- document_id
- source_file
- page_index
- text
- char_count
- extraction_status

## Audit Fields

Audit should include:

- pdf_count
- page_count
- chars_total
- texty_pages
- err_pages
- text_based_count
- possibly_image_based_count
- output paths
- blocked claims

## Dependency Policy

Preferred dependency:

```text
pypdf
```

Fallback:

```text
PyPDF2
```

If neither is installed:

```text
PDF_EXTRACTION_DEPENDENCY_MISSING
```

In that case, file manifest may still be written, but page extraction must fail closed.

## Fitness PDF Rule

Fitness PDFs can be indexed and extracted as support documents.

They cannot be absorbed into tactical analysis as direct tactical truth.

Safe phrasing:

```text
Fitness PDF support evidence is available and can be reviewed beside ACTIVE_MATCH event evidence.
```

Unsafe phrasing:

```text
The PDF proves fatigue caused the tactical pattern.
```

## Acceptance Criteria

This node can reach ACTIVE_MATCH_EVIDENCE_PASS or SUPPORT_EVIDENCE_PASS only if:

1. module compiles;
2. tests pass;
3. PDF files are indexed with SHA256;
4. page-level JSONL is written;
5. extraction audit is written;
6. no fitness/tactical/fatigue truth is emitted;
7. outputs are flat under allowed phone root.

## Current Status

```text
P2B_CONTRACT_SPEC_WRITTEN
IMPLEMENTATION_NOT_STARTED
ACTIVE_MATCH_EXECUTION_NOT_RUN
```
