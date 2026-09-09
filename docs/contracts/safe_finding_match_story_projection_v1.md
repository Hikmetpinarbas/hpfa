# Safe Finding Match Story Projection V1

## Purpose

Project only already-emitted `sequence_safe_finding_binding_lite_v1` professional findings into a compact analyst-facing match-story candidate. This is a presentation projection inside the existing professional-finding module, not a new discovery, sequence, episode, metric, tactical or causal engine.

## Required upstream state

A story candidate is eligible only when the upstream row is `finding_status=EMIT`, `professional_finding_emitted=true`, and `claim_output_allowed=true` with explicit SAFE_MEANING, WHERE_WHEN, SUPPORT, COUNTEREVIDENCE and withdrawal condition.

DOWNGRADE and ABSTAIN rows never become match-story candidates.

## Claim locks

Every story candidate preserves:

- `canonical_event_count=UNKNOWN`
- `true_action_count=UNKNOWN`
- `production_release=false`
- story order != football chronology truth
- story != possession truth
- story != tactical phase truth
- story != formation/team-shape truth
- story != true-pressure truth
- story != coach-intention truth
- story != dominance truth
- story != causality truth
- story != stable team-tendency truth

The projection must retain explicit counterevidence and withdrawal surfaces. Missing challenge/withdrawal surfaces require review rather than prose promotion.

## Acceptance boundary

GitHub CI is engineering evidence only. Physical canonical ACTIVE_MATCH evidence is separately required before claiming that this new story projection produced defensible real-match analyst evidence on the authoritative phone runtime.
