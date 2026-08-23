# HPFA Intelligence Fusion Upstream Failure Propagation V1

Status: `REVIEW_REQUIRED / P0_CORRECTION_IMPLEMENTED / CI_PENDING / NOT_PRODUCTION`

## Problem

`composite_evidence_packet_builder_lite_v1` can fail closed while still carrying populated candidate fields. Before this correction, `multi_signal_evidence_fusion_lite_v1` validated shape/claim fields but did not explicitly reject an already failed upstream packet.

This allowed an upstream packet with any of the following to reach local fusion relation construction:

```text
hard_block_hits non-empty
status=FAIL_CLOSED or BLOCKED
decision=BLOCK_*
```

This is an integration correctness problem, not a football-truth problem.

## Current correction

`multi_signal_evidence_fusion_lite_v1` now uses:

```text
_upstream_packet_failed(packet)
```

and appends:

```text
upstream_packet_failed_closed
```

when upstream packet failure is present.

The fusion output also preserves:

```text
upstream_status
upstream_decision
upstream_hard_block_hits
```

so the block reason is traceable rather than silently replaced by local fusion status.

## Regression requirements

```text
test_failed_upstream_packet_blocks_fusion
test_block_packet_decision_blocks_fusion
test_packet_hard_block_hits_propagate_to_fusion
```

Existing boundaries remain required:

```text
canonical_event_count=UNKNOWN
claim_output_allowed=false
report_language_allowed=false
no tactical/dominance/control/coach-intention/off-ball/pitch-control/causal truth
nested phone output rejected
test_no_sample_match_identity_leak
```

## Engineering evidence boundary

This change requires exact-head CI. No ACTIVE_MATCH football result is claimed by this document.

## Analyst evidence boundary

No analyst-facing match finding is produced by this correction. Its analyst value is indirect but important: evidence that upstream failed review/quality gates cannot be revived by a downstream fusion layer and later appear as apparently valid analyst evidence.

## Next P0 integration blockers

After this correction:

1. recursive/path-aware forbidden-field guard across Packet/Fusion/Argument;
2. explicit review-debt propagation across Fusion -> Argument -> Defeasible -> Graph -> Safe Router;
3. canonical `argument -> defeasible route -> evidence graph` contract;
4. end-to-end match-agnostic Intelligence Layer contract fixture.

These are current-product hardening tasks. They take priority over importing new donor intelligence capability.

## Claim / release locks

```text
canonical_event_count=UNKNOWN
production_release=false
PASS != RELEASE
MERGED != PRODUCTION_RELEASE
```
