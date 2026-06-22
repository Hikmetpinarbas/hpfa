# HPFA Phone Output Policy Audit V1

Date: 2026-06-22

Status: P0A_GOVERNANCE_FILE

## Policy

User-visible Termux outputs must be written flat under one of these roots:

```text
/sdcard/Download/HPFA
/storage/emulated/0/Download/HPFA
```

Nested output directories under those roots are rejected.

Rejected example:

```text
/sdcard/Download/HPFA/spine-run/output.txt
```

Required rejection marker:

```text
nested_phone_output_directory_rejected
```

## Current Product Guard

The active spine runner defines phone output roots and validates output directories before writing outputs.

Accepted:

```text
/sdcard/Download/HPFA
/storage/emulated/0/Download/HPFA
```

Rejected:

```text
/sdcard/Download/HPFA/<nested-directory>
/storage/emulated/0/Download/HPFA/<nested-directory>
```

## P1 Requirement

P1 ACTIVE_MATCH Analyst Report Lite V1 must write exactly these flat user-visible outputs:

```text
/sdcard/Download/HPFA/active_match_analyst_report_lite_v1.json
/sdcard/Download/HPFA/active_match_analyst_report_lite_v1.txt
```

or equivalent under:

```text
/storage/emulated/0/Download/HPFA
```

P1 must not write:

```text
/sdcard/Download/HPFA/active-match-analyst-report-lite-v1/active_match_analyst_report_lite_v1.json
/sdcard/Download/HPFA/p1/active_match_analyst_report_lite_v1.txt
```

## Output Evidence Rule

A module may claim phone-output evidence only when:

1. output path is one of the flat phone roots;
2. required files are written directly under that root;
3. nested path rejection is tested;
4. output names match the module contract;
5. ACTIVE_MATCH execution is recorded when runtime evidence is required.

## Audit Result

Phone output policy status:

```text
FLAT_PHONE_OUTPUT_POLICY_LOCKED
NESTED_PHONE_OUTPUT_REJECTION_REQUIRED
```

This file is governance evidence. It is not ACTIVE_MATCH execution evidence and not product release proof.
