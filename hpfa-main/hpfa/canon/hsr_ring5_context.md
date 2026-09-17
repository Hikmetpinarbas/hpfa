# HSR Ring 5 — Context / Temporal (Fail-Closed)

## Rules

- **Temporal monotonicity**: `event_start_time >= prev_event_time` zorunlu.
- **START landing invariant**: `possession_effect == START` ise `state_id` her zaman
  `CONTROLLED` olmalıdır. Kaynak state kısıtlı değildir — DEAD_BALL (RESTART_*),
  CONTROLLED (INTERCEPTION) veya CONTESTED (INTERCEPTION) hepsi geçerlidir.
  Canon: possession_state_machine.md satır 36–41.
- **Restart cooldown**: `prev_state_id == DEAD_BALL` iken 0.3 saniyeden sonra
  TACKLE veya INTERCEPTION gelirse veto (fizik ihlali).
- **Eksik alanlar**: `event_start_time`, `prev_event_time`, `state_id`, `prev_state_id`
  herhangi biri yoksa FAIL-CLOSED (ValueError).
