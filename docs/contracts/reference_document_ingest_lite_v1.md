# HPFA Reference Document Ingest Lite V1 Contract

Date: 2026-06-22

Status: ACTIVE_MATCH_EVIDENCE_PASS

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

This node can reach ACTIVE_MATCH_EVIDENCE_PASS only if:

1. module compiles;
2. tests pass or evidence bundle explicitly records runtime-only documentation scope;
3. PDF files are indexed with SHA256;
4. page-level JSONL is written;
5. extraction audit is written;
6. no fitness/tactical/fatigue truth is emitted;
7. outputs are flat under allowed phone root;
8. module_governance_matrix.tsv is synchronized.

## Current Evidence

Runtime evidence reported by operator:

```text
module_id=reference_document_ingest_lite_v1
status=REFERENCE_DOCUMENT_INGEST_PASS
claim_safety=REFERENCE_ONLY_SUPPORT_SIGNAL
active_match_mode=True
pdf_count=5
page_count=141
chars_total=284238
texty_pages=134
err_pages=0
runtime_event_truth=False
output_root=/storage/emulated/0/Download/HPFA
```

Observed output files:

```text
/storage/emulated/0/Download/HPFA/reference_document_manifest_v1.json
/storage/emulated/0/Download/HPFA/reference_document_pages_v1.jsonl
/storage/emulated/0/Download/HPFA/reference_document_extraction_audit_v1.json
/storage/emulated/0/Download/HPFA/reference_document_extraction_audit_v1.txt
```

Extracted documents:

```text
0001_australia_turkey_fitness_players_eng | pages=33 | chars=93040 | status=PDF_EXTRACTION_PASS
0002_australia_turkey_fitness_players_tur | pages=33 | chars=96529 | status=PDF_EXTRACTION_PASS
0003_australia_turkey_fitness_report      | pages=11 | chars=30356 | status=PDF_EXTRACTION_PASS
0004_australia_turkey_form_raporu         | pages=11 | chars=30284 | status=PDF_EXTRACTION_PASS
0005_australia_turkey_fifa_report         | pages=53 | chars=34029 | status=PDF_EXTRACTION_PASS
```

Blocked claims preserved:

```text
fatigue truth
load truth
injury truth
tactical truth
dominance truth
event truth override
```

## Current Status

```text
ACTIVE_MATCH_EVIDENCE_PASS
REFERENCE_DOCUMENT_INGEST_PASS
PRODUCTION_RELEASE_NOT_GRANTED
```

Reason:

- Runtime evidence proves five ACTIVE_MATCH-adjacent PDFs were indexed and extracted.
- Page-level JSONL and extraction audit were written under allowed flat phone output root.
- The module preserved `runtime_event_truth=False`.
- The module did not emit fatigue, load, injury, tactical, dominance or event-truth override claims.
- The canonical governance matrix row is synchronized to `ACTIVE_MATCH_EVIDENCE_PASS` in this branch.

Not production release:

- Reference Concept Extractor Lite is still missing.
- Reference-Supported Tactical Claim Lite is still missing.
- Claim gate integration remains required before reference-supported tactical language.
