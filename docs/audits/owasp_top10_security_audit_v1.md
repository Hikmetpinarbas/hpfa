# HPFA OWASP Top 10 Security Audit V1

Status: `REVIEW_REQUIRED`

## Scope

Repository: `Hikmetpinarbas/hpfa`

Primary attack surface reviewed:

```text
Python CLI entrypoints
ACTIVE_MATCH file ingest
CSV/XML/XLSX parsing
subprocess execution
phone output paths
runtime import paths
archive handling
```

This repository is not currently a web application. No HTTP routing, browser template rendering, database query layer, cookie/session layer or authentication endpoint was identified in the reviewed main surface.

## Executive result

```text
Critical confirmed findings: 0
High confirmed findings: 1
Medium confirmed findings: 2
Low confirmed findings: 1
Not-applicable OWASP categories: SQL injection, XSS and web-session specific controls
```

## Confirmed findings

### SEC-001 — Unbounded XML/XLSX parsing and archive expansion

Severity: `HIGH`

OWASP mapping:

```text
A04 Insecure Design
A05 Security Misconfiguration
A08 Software and Data Integrity Failures
```

Affected surfaces:

```text
canonical_ingest_surface_manifest
ACTIVE_MATCH analyst report ingest
legacy hpfa ingest tooling
```

Risk:

```text
malicious or malformed XML can consume excessive CPU/memory
XLSX ZIP members can expand far beyond compressed size
large files and excessive row counts can exhaust Termux resources
DTD/entity declarations were not rejected before parsing
```

Correction:

```text
regular-file and symlink validation
maximum file size
XML DTD/entity rejection
XLSX entry-count limit
XLSX uncompressed-size limit
per-entry size limit
compression-ratio limit
bounded row count
fail-closed security error vocabulary
```

### SEC-002 — Shell execution in runtime audit tool

Severity: `MEDIUM`

OWASP mapping:

```text
A03 Injection
A05 Security Misconfiguration
```

Affected file:

```text
tools/audit_runtime_paths.py
```

Risk:

```text
shell pipeline dependency
PATH-based executable substitution risk
unnecessary command interpreter exposure
unbounded external process duration
```

Correction:

```text
os.system removed
subprocess.run uses argv list
sys.executable used instead of ambient python command
timeout added
stdout/stderr bounded to first 120 lines
```

### SEC-003 — Symlink surface traversal

Severity: `MEDIUM`

OWASP mapping:

```text
A01 Broken Access Control
A04 Insecure Design
```

Risk:

A symlink placed inside an ACTIVE_MATCH directory could point outside the intended match authority and cause an unrelated local file to be read as an event surface.

Correction:

```text
surface symlinks rejected
only regular files accepted
security failure is explicit and fail-closed
```

### SEC-004 — Broad exception swallowing in diagnostic tooling

Severity: `LOW`

OWASP mapping:

```text
A09 Security Logging and Monitoring Failures
```

Risk:

Some legacy diagnostic utilities suppress exceptions and continue, reducing forensic clarity.

Current action:

```text
recorded for later refactor
not a release blocker for the current product path
```

## OWASP category assessment

### A01 Broken Access Control

Result: `PARTIAL_RISK_FOUND`

No user/role authorization system exists. File-boundary risk existed through symlink-following and was corrected in the secured ingest path.

### A02 Cryptographic Failures

Result: `NOT_APPLICABLE_CURRENT_SURFACE`

No password store, session secret, payment data or encrypted transport implementation was found. Input/output hashes are integrity evidence, not authentication.

### A03 Injection

Result: `PARTIAL_RISK_FOUND`

No SQL engine or browser template layer was found. Therefore SQL Injection and XSS are not currently applicable. Shell execution in a diagnostic tool was removed.

### A04 Insecure Design

Result: `RISK_FOUND_AND_CORRECTED`

Unbounded file parsing and implicit trust of local event surfaces were the main design weaknesses.

### A05 Security Misconfiguration

Result: `RISK_FOUND_AND_CORRECTED`

Resource limits, archive limits and parser preflight controls were missing.

### A06 Vulnerable and Outdated Components

Result: `NOT_PROVEN`

A dependency lock and automated vulnerability scan were not found in the reviewed surface. No claim is made that dependencies are current or vulnerable.

Required later evidence:

```text
pinned dependency inventory
pip-audit or equivalent scan
SBOM
update policy
```

### A07 Identification and Authentication Failures

Result: `NOT_APPLICABLE_CURRENT_SURFACE`

No authentication system exists in the current CLI product.

### A08 Software and Data Integrity Failures

Result: `PARTIAL_RISK_FOUND`

Untrusted XML/XLSX structures entered parsing without archive-integrity constraints. The secured path now validates structure and resource bounds before parsing.

### A09 Security Logging and Monitoring Failures

Result: `PARTIAL_GAP`

Security failures are now emitted as deterministic error strings in the secured product path. Legacy utilities still contain broad exception suppression.

### A10 Server-Side Request Forgery

Result: `NOT_APPLICABLE_CURRENT_SURFACE`

No server-side URL fetcher or user-controlled outbound HTTP request path was found.

## SQL Injection and XSS conclusion

```text
SQL Injection: NOT_APPLICABLE — no SQL query layer found
XSS: NOT_APPLICABLE — no HTML/template/browser rendering layer found
```

This is not a guarantee for future web/API components. Any future HTTP, database or browser consumer requires a new threat model.

## Secure architecture introduced

```text
ACTIVE_MATCH surface
-> secure_surface_manifest preflight
-> regular-file boundary
-> XML/XLSX resource and structure validation
-> legacy semantic inventory only after security PASS
-> spine/report fail closed on security failure
```

## Tests added

```text
symlink surface rejection
XML DOCTYPE rejection
invalid XLSX archive rejection
small valid XLSX acceptance
```

## Remaining risks

```text
legacy tools/hpfa_ingest_v1.py still parses XML/XLSX directly
no automated dependency vulnerability scan
no SBOM
no repository-wide secret scan evidence
no executed test evidence for this branch yet
```

## Release readiness

```text
security design: POLICY_CORRECTION_PASS
implementation: WRITTEN
unit tests: WRITTEN_NOT_EXECUTED
ACTIVE_MATCH regression: REQUIRED
production release: NOT_READY
```
