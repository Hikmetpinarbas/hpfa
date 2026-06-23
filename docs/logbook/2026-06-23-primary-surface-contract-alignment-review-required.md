# HPFA Project Logbook Entry — 2026-06-23

## Session Summary

Session title: Primary Event Surface Gate Contract Alignment

Node:

```text
Primary Event Surface Gate Lite V1
```

Summary:

- Codex review identified two contract alignment issues after PR #33.
- The gate emitted a non-contract decision value when overlap candidates were present.
- The gate selected a heuristic top surface even when more than one event surface was eligible.
- The hotfix restores contract behavior: unresolved state is required until overlap and multi-surface ambiguity are cleared.

## Engineering Evidence

Code changes:

```text
primary_event_surface_candidate remains UNRESOLVED when review conditions exist.
top_candidate_for_review preserves the best surface for analyst/operator review.
downstream unlocks remain WAIT while unresolved reasons exist.
```

Regression tests added:

```text
test_multiple_eligible_surfaces_return_unresolved
test_overlap_candidates_keep_unresolved_boundary
```

## Analyst Evidence

Safe analyst reading:

```text
Players CSV may remain the strongest candidate for review, but ACTIVE_MATCH still requires review because overlap candidates and multiple eligible event surfaces remain visible.
```

## Claim Boundary

Allowed:

- top candidate for review;
- unresolved primary surface state;
- overlap review requirement;
- multiple eligible surface review requirement.

Blocked:

- heuristic candidate as selected primary surface;
- selected candidate as event truth;
- selected candidate as downstream unlock while overlap remains.

## Product Status

Normalized status:

```text
REVIEW_REQUIRED
```

Reason:

```text
The module has been corrected, but ACTIVE_MATCH rerun is required before evidence status can be restored.
```

## Next Correct Step

Run local validation on the hotfix branch:

```text
python -m py_compile primary_event_surface_gate.py hpfa/modules/core/primary_event_surface_gate_lite/src/primary_event_surface_gate.py
pytest hpfa/modules/core/primary_event_surface_gate_lite/tests/test_primary_event_surface_gate.py
python primary_event_surface_gate.py --out-dir /sdcard/Download/HPFA
```

Expected ACTIVE_MATCH behavior:

```text
decision=UNRESOLVED_REVIEW_REQUIRED
primary_event_surface_candidate=UNRESOLVED
top_candidate_for_review.source_role=players
```
