# NAS — Negative Action Spiral (Canonical v1.0.0)

## Purpose
NAS, savunma fazında aynı bölgede kısa zaman aralığında oluşan ardışık başarısız aksiyon zincirlerini deterministik ve fail-closed şekilde tespit eder.

## Scope
- phase ∈ {DEFENSIVE, TRANSITION} dışı olaylar NAS evreni dışıdır (ignore).
- HSR veto durumları NAS'a dahil edilmez (exclude).

## Required Event Fields (Fail-Closed)
- ts: float  (event_start_time)
- phase: str
- state_id: str
- action_type: str
- outcome: str
- zone_id: str|int
- pressure_level: float|int
- hsr_flags: dict
  - ring3_dead_ball_veto: bool
  - ring4_physics_veto: bool

Eksik alan → status=UNVALIDATED, reason=NAS_FAIL_CLOSED:missing_<field>

## Hard Gates (Exclude)
1) phase not in {DEFENSIVE, TRANSITION}  => ignore
2) state_id == DEAD_BALL or ring3_dead_ball_veto == True => ignore
3) ring4_physics_veto == True => ignore
4) outcome != FAIL => ignore

## Deterministic Rule
- Aynı zone_id içinde,
- ardışık FAIL olayları arasında Δt ≤ 0.5s,
- FAIL sayısı ≥ 3 olursa bir NAS sequence oluşur.

**Zaman kuralı kilitli:** Δt ardışık event-to-event delta’dır.
Sequence uzasa bile count=1 kalır; fail_count artar.

## Break Conditions
- zone değişimi
- Δt > 0.5s
- outcome != FAIL
- phase scope dışına çıkış
- ring3/ring4 veto veya DEAD_BALL

## Outputs
- NAS_Sequence_Count: int
- NAS_Sequences: list[{start_ts,end_ts,zone_id,fail_count,avg_pressure,max_pressure,event_ids?}]
- status: PASS|UNVALIDATED
