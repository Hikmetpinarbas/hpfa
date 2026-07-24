# Cross-Format Reconciliation Lite V1

## Scope

This node binds visible CSV, XML and XLSX surface evidence to runtime bytes,
inventory hashes and provider-semantic provenance. It produces candidate-only
cross-format alignment evidence.

It does not produce canonical events, validated identities, independent XLSX
confirmation, aggregate-definition truth, phase, possession, sequence or
tactical truth.

## Source binding

Every reader file record must carry a valid SHA-256. The runtime file is
re-hashed and must equal both the reader audit SHA and an inventory SHA for the
same relative path. Missing or unequal hashes fail closed.

Exact duplicate reflections from the inventory and local duplicate candidates
are separate counts. Reflections are not re-counted as surface-row volume.

## Semantic separation

Field-path semantics and provider label-value semantics are separate inputs.
Field mapping coverage cannot substitute for label-value semantics coverage.
Reviewed exact label rules precede token fallback. Token fallback and
multi-anchor conflicts remain review-only and downstream-blocked.

The XML group registry maps visible group-label values to candidate field keys.
It is versioned, source-referenced and explicitly candidate-only. It does not
grant XML priority or validated provider semantics.

## Reconciliation evidence

Candidate signatures are emitted both with and without row identity. The
cross-ID collision check uses the signature without identity. Present/present
support, both-missing support and one-missing support are reported separately.
Both-missing values are not exact support.

`active_match_evidence_pass=true` requires:

- exact runtime-authority equality;
- `status=PASS`;
- zero hard blocks;
- zero review warnings.

`canonical_event_count=UNKNOWN` and `production_release=false` are invariant.
