# Multiformat File Inventory Lite V1

Status: `IMPLEMENTED_NOT_RUNTIME_PROVEN`

## Purpose

Discover and inventory CSV, TSV, XLSX, XLS, XML, JSON and JSONL surfaces recursively before any semantic join, event admission or aggregate reconciliation.

This module is the first executable node under Issue #163.

## Source role

- Product source: current `Hikmetpinarbas/hpfa` branch.
- Runtime authority: `runtime/active_single_match/current`.
- Google Drive and donor materials: `REFERENCE_ONLY / DONOR_SUPPORT`.
- Donor rule: `ADAPT_NOT_COPY`.

## Inputs

A selected input root, normally the ACTIVE_MATCH runtime directory.

Supported extensions:

```text
.csv .tsv .xlsx .xls .xml .json .jsonl
```

Unsupported files are reported rather than silently discarded.

## Count semantics

```text
total_file_path_count = supported_file_count + unsupported_file_count
supported_file_count = paths with a supported extension
unique_content_file_count = unique SHA-256 fingerprints among supported files
file_count = legacy alias of supported_file_count
```

These counts must not be substituted for one another. In particular, `file_count`
does not represent every visible path when unsupported reference or governance files
are present.

## Per-file output

```text
file_id
file_name
relative_path
extension
mime_type
size_bytes
sha256
encoding_candidate
bom_present
delimiter_candidate
quote_character_candidate
sheet_names
sheet_states
xml_root_tag
xml_namespace_map
surface_row_count
visible_column_count
source_role
provider_candidate
match_identity_candidate
readability_status
parse_status
schema_fingerprint
hard_block_hits
parse_warnings
canonical_event_count
claim_ceiling
```

## Safety and interpretation

- Surface rows are not canonical events.
- Same hash means exact file duplication, not duplicate event truth.
- Same filename with different hashes is a conflicting file-surface condition.
- Unsupported extension is review-required, not silently ignored.
- Empty and unreadable files fail closed.
- XML DTD and entity declarations are blocked before parsing.
- XLSX workbook metadata is read without treating sheets as event truth.
- Legacy XLS is inspected through a signature check and an optional legacy reader.
- Filename-derived source roles remain candidates.
- Provider and match identities remain unknown candidates.
- `canonical_event_count=UNKNOWN`.
- `active_match_evidence_pass=false`.
- `production_release=false`.

## Hard blocks

```text
input_root_missing
file_unreadable
unsupported_encoding
encrypted_xlsx
malformed_xml
malformed_json
empty_file
duplicate_file_conflict
external_entity_resolution_attempted
nested_phone_output_directory_rejected
```

## Flat outputs

```text
multiformat_file_inventory_lite_v1.json
input_file_inventory.json
input_file_inventory.tsv
unsupported_file_report.json
duplicate_file_fingerprint_report.json
multiformat_ingest_decision_v1.txt
```

## Acceptance tests

Deterministic tests cover:

- recursive discovery;
- SHA-256 manifest generation;
- delimiter and encoding detection;
- XLSX sheet and hidden-sheet inventory;
- XML namespace handling;
- XML external-entity blocking;
- exact duplicate reporting;
- conflicting same-name file detection;
- empty input files;
- missing input roots;
- unsupported-file reporting;
- flat output policy;
- nested phone-output rejection;
- sample match identity leak prevention;
- canonical event count protection.

## Release status

Successful unit/integration tests establish only `SMOKE_PASS`.

`ACTIVE_MATCH_EVIDENCE_PASS` requires a real run against `runtime/active_single_match/current`.

`PRODUCTION_RELEASE` is a separate explicit decision.
