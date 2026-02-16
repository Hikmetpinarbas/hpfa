from engine.possession import (
    CanonEvent, PossessionState, EpistemicStatus,
    EventType, Outcome, ShotOutcome, simulate
)

events = [
    # Restart -> new possession, controlled
    CanonEvent(event_id="e1", team_id=1, player_id=10, event_type=EventType.RESTART, outcome=Outcome.SUCCESS),

    # Pass success -> stays controlled
    CanonEvent(event_id="e2", team_id=1, player_id=10, event_type=EventType.PASS, outcome=Outcome.SUCCESS),

    # Pass fail -> contested
    CanonEvent(event_id="e3", team_id=1, player_id=10, event_type=EventType.PASS, outcome=Outcome.FAIL),

    # Interception success by team 2 -> controlled new possession
    CanonEvent(event_id="e4", team_id=2, player_id=6, event_type=EventType.INTERCEPTION, outcome=Outcome.SUCCESS),

    # Shot saved, GK holds -> controlled new possession for GK team (2)
    CanonEvent(event_id="e5", team_id=2, player_id=1, event_type=EventType.SHOT, shot_outcome=ShotOutcome.SAVED, qualifiers={"GK_HOLDS": True}),

    # Out -> dead ball
    CanonEvent(event_id="e6", team_id=2, player_id=1, event_type=EventType.OUT, outcome=Outcome.SUCCESS),

    # Restart -> controlled new possession
    CanonEvent(event_id="e7", team_id=1, player_id=10, event_type=EventType.RESTART, outcome=Outcome.SUCCESS),

    # Missing identity -> UNVALIDATED fail-closed
    CanonEvent(event_id="e8", team_id=None, player_id=10, event_type=EventType.PASS, outcome=Outcome.SUCCESS),

    # Epistemic UNVALIDATED upstream -> UNVALIDATED
    CanonEvent(event_id="e9", team_id=1, player_id=10, event_type=EventType.PASS, outcome=Outcome.SUCCESS, epistemic=EpistemicStatus.UNVALIDATED),
]

frames = simulate(events, scramble_timeout_events=3)

for f in frames:
    print(
        f.event_id,
        f.state_before, "->", f.state_after,
        "pid:", f.possession_id_before, "->", f.possession_id_after,
        "team:", f.possessing_team_before, "->", f.possessing_team_after,
        "flags:", f.flags
    )

# Minimal assertions
assert frames[0].state_after == PossessionState.CONTROLLED
assert frames[2].state_after == PossessionState.CONTESTED
assert frames[3].state_after == PossessionState.CONTROLLED
assert frames[5].state_after == PossessionState.DEAD_BALL
assert frames[7].state_after == PossessionState.UNVALIDATED
print("✅ POSSESSION TESTS PASSED")
