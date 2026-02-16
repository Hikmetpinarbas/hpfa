from validators.epistemic import Event, EpistemicStatus, evaluate_epistemic_status

event = Event(
    player_id=10,
    team_id=1,
    event_type="PASS",
    zone=12
)

status = evaluate_epistemic_status(event)
print(status)
