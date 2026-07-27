# Visible Action Sequence Candidate Admission Lite V1

## Amaç

Bu düğüm, selected-action ve selected-event consequence yüzeylerini doğrudan possession veya phase truth ilan etmeden, görünür zaman katmanları ve same-team continuity adayları halinde düzenler.

```text
Selected Action Consequence Surface V1.1
+ Selected Event Consequence Surface V1
→ Visible Time-Layer Candidates
→ Sequence Admission
→ Boundary Candidates
→ Trace Signals
```

## Primary ve context ayrımı

Sequence için primary node yalnız şu rollerden gelir:

```text
PLAYER_SURFACE_CANDIDATE
GOALKEEPER_SURFACE_CANDIDATE
```

ve actor identity applicability:

```text
APPLICABLE_BOUND_CANDIDATE
```

olmalıdır.

`TEAM_SURFACE_CANDIDATE` kayıtları sequence event gibi sayılmaz. Bunlar:

```text
TEAM_CONTEXT_SUPPORT
```

olarak time-layer veya sequence candidate'a bağlanır. Böylece takım aggregate/reflection yüzeyleri fiziksel action sayısını şişirmez.

## Visible time-layer

Aynı period ve aynı start-time candidate içindeki bütün node'lar tek layer'da tutulur.

Layer durumları:

```text
SINGLE_TEAM_PRIMARY_LAYER
MIXED_TEAM_PRIMARY_LAYER_REVIEW_REQUIRED
TEAM_CONTEXT_ONLY_LAYER
UNKNOWN_PRIMARY_LAYER_REVIEW_REQUIRED
```

Aynı timestamp içindeki node'lar sıralanmaz:

```text
same_timestamp_internal_ordering_allowed=false
```

## Sequence admission

Sequence candidate yalnız şu koşullarla kurulur:

```text
same match-surface binding
same period
strictly increasing primary-layer start time
same team identity candidate
gap <= 12 seconds
no mixed-team primary layer crossing
actor-bound restart boundary respected
```

Actor-bound restart family yeni sequence candidate başlatabilir. TEAM-surface restart support tek başına sequence split oluşturmaz.

## Boundary candidates

```text
PERIOD_END
TIME_GAP_BOUNDARY
TEAM_HANDOVER_BOUNDARY
RESTART_PRIMARY_LAYER_BOUNDARY
MIXED_TEAM_PRIMARY_LAYER_BOUNDARY
TEAM_CONTEXT_ONLY_LAYER_BOUNDARY
TERMINAL_OUTCOME_SUPPORT_BOUNDARY
```

Team handover boundary possession change truth değildir.

## Trace signal candidates

```text
OPEN_VISIBLE_CONTINUITY_CANDIDATE
RESTART_TRACE_CANDIDATE
REGAIN_TO_VISIBLE_CONTINUATION_CANDIDATE
SHOT_CHAIN_CANDIDATE
CLEARANCE_CLUSTER_CANDIDATE
PROGRESSION_TO_HANDOVER_TRACE_CANDIDATE
TURNOVER_TO_OPPONENT_SHOT_TRACE_CANDIDATE
TURNOVER_TO_OPPONENT_BOX_ACCESS_TRACE_CANDIDATE
```

Ayrıca sequence içindeki constructive, risky-constructive, failed ve unresolved consequence context yalnız composition signal olarak taşınır.

## Node assignment reconciliation

Her selected-action node tam olarak bir assignment alır:

```text
PRIMARY_SEQUENCE_MEMBER
REVIEW_LAYER_MEMBER
TEAM_CONTEXT_SUPPORT_ATTACHED_TO_SEQUENCE
TEAM_CONTEXT_ONLY_LAYER_SUPPORT
```

Eksik veya çift assignment fail-closed olur.

## Donor map — ADAPT_NOT_COPY

- current `hpfa` selected consequence producers ve event-window contract = product authority;
- HP-Motor possession-bounded sequence split = donor support;
- HP-Engine period/restart/gap/team-change split = donor support;
- Google Drive event-chain ve applied-reading belgeleri = REFERENCE_ONLY;
- Dropbox sequence-window, trace-type ve safe-language dosyaları = method/language donor.

Donor kodu doğrudan kopyalanmaz ve donor kaynak ACTIVE_MATCH authority olamaz.

## Analyst-facing anlam

Bu düğüm şu sorulara candidate evidence üretir:

- Aynı takımın actor-bound görünür aksiyonları kısa zaman aralığında zincir oluşturuyor mu?
- Zincir hangi boundary ile başladı ve bitti?
- Zincirde restart, regain, shot, clearance veya progression-to-handover sinyali var mı?
- Zincir içinde constructive, failed veya unresolved consequence context hangi yoğunlukta?
- Team-surface context hangi sequence'lere destek veriyor?

## Claim boundary

```text
visible_sequence_candidate_is_sequence_truth=false
visible_sequence_candidate_is_possession_truth=false
single_team_continuity_is_control_truth=false
restart_trace_is_set_piece_design_truth=false
shot_chain_is_chance_quality_truth=false
progression_to_handover_is_bad_decision_truth=false
sequence_duration_is_physical_action_duration=false
analysis_sentence_generated=false
event_instance_count=0
claim_allowed=false
phase_truth=false
possession_truth=false
sequence_truth=false
tactical_truth=false
canonical_event_count=UNKNOWN
production_release=false
```
