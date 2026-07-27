# Selected Event Consequence Surface Lite V1

## Amaç

Bu düğüm, `selected_action_consequence_surface_lite_v1` çıktısını categorical-first futbol zekâsı yüzeyine dönüştürür.

```text
Selected Action Consequence Surface V1.1
→ Coordinate Frame Candidate
→ Zone Delta Candidate
→ Turnover Window Candidate
→ Retention / False-Progression Candidate
→ Categorical Consequence Class
```

Numeric value, xT, VAEP, goal probability, possession truth veya tactical truth üretmez.

## Coordinate frame candidate

Coordinate scale yalnız görünür sınırlar destekliyorsa candidate olarak yükseltilir:

- `PROVIDER_105X68_SCALE_CANDIDATE`
- `PROVIDER_100X100_SCALE_CANDIDATE`
- `UNRESOLVED_COORDINATE_SCALE_REVIEW_REQUIRED`

Attack direction, her team-period için shot-coordinate concentration ile candidate olarak çözülür. En az üç shot-support node gerekir. Median ve concentration guard’ları geçmezse direction unresolved kalır.

```text
ATTACK_TOWARD_HIGH_X_CANDIDATE
ATTACK_TOWARD_LOW_X_CANDIDATE
UNRESOLVED_ATTACK_DIRECTION_REVIEW_REQUIRED
```

Bu işlem provider coordinate truth veya validated attack direction üretmez.

## Zone grid

Coordinate frame candidate geçerse görünür koordinatlar şu categorical grid’e ayrılır:

- own third candidate;
- middle third candidate;
- final third outside box candidate;
- final-third wide/outside-box-band candidate;
- box-coordinate candidate;
- central deep-box grid candidate.

Central deep-box grid, goal probability veya high-value truth değildir.

## Zone delta

Zone delta yalnız aynı takımın ilk görünür katmanı için hesaplanır. Rakip yüzeyle coordinate farkı alınmaz.

```text
NO_VISIBLE_FOLLOW_UP_CANDIDATE
LOSS_OR_HANDOVER_CANDIDATE
NO_ZONE_CHANGE_CANDIDATE
RESET_OR_BACKWARD_ZONE_CHANGE_CANDIDATE
ZONE_GAIN_CANDIDATE
THIRD_BREAK_CANDIDATE
BOX_ACCESS_CANDIDATE
CENTRAL_DEEP_BOX_ENTRY_CANDIDATE
MIXED_SAME_TEAM_ZONE_REVIEW_REQUIRED
UNRESOLVED_ZONE_DELTA_REVIEW_REQUIRED
```

## Pressure field

Current event-only yüzeyde tracking veya explicit pressure event bulunmadığı için `none` yazılmaz.

```text
pressure_first_action_class=
UNAVAILABLE_EVENT_ONLY_NO_EXPLICIT_PRESSURE_EVIDENCE
```

Bu ayrım “baskı yoktu” iddiasını engeller.

## Turnover window

Turnover ve control-error family anchor’ları için görünür 12 saniye / üç time-layer yüzeyi sınıflandırılır:

- same-team recovery;
- same-team retention;
- opponent handover;
- opponent box access;
- opponent shot;
- no visible response;
- mixed veya unresolved review.

Bu sınıflar counterpress success, transition superiority veya player failure truth değildir.

## Retention after action

Tri-state candidate:

```text
true  → first visible layer same team
false → first visible layer opponent
null  → mixed, none veya unresolved
```

Her boolean yanında explicit status bulunur. Possession truth üretilmez.

## False progression candidate

False-progression candidate yalnız şu minimum görünür koşullarda açılır:

1. aynı takımın ilk görünür katmanında zone gain candidate;
2. sonraki görünür katmanda rakip handover;
3. rakip handover öncesinde same-team shot support yok.

Bu sınıf kötü karar, oyuncu hatası veya progression quality truth değildir.

## Consequence class candidate

Deterministic precedence ile üretilir:

```text
CONSTRUCTIVE_VISIBLE_CONSEQUENCE_CANDIDATE
RISKY_CONSTRUCTIVE_VISIBLE_CONSEQUENCE_CANDIDATE
NEUTRAL_VISIBLE_CONSEQUENCE_CANDIDATE
FAILED_VISIBLE_CONSEQUENCE_CANDIDATE
UNRESOLVED_VISIBLE_CONSEQUENCE_REVIEW_REQUIRED
```

Bu alan analist-facing categorical consequence yüzeyidir; value veya quality değildir.

## Profiller

- team + action-family event-consequence profile;
- actor + action-family event-consequence profile;
- zone-delta dağılımı;
- turnover-window dağılımı;
- retention dağılımı;
- false-progression dağılımı;
- consequence-class dağılımı.

## Donor sınırı

- current hpfa producer = product authority;
- uploaded operator specs = specification support;
- Google Drive action/reaction ve coordinate-normalization belgeleri = REFERENCE_ONLY;
- Dropbox `CONSEQUENCE_MAPPING_RULES_B05.csv` = method donor;
- yöntem `ADAPT_NOT_COPY`;
- donor kaynaklar ACTIVE_MATCH evidence’i override etmez.

## Claim boundary

```text
consequence_not_value=true
consequence_not_quality=true
zone_delta_not_xT=true
zone_delta_not_progression_truth=true
pressure_escape_not_pressure_truth=true
turnover_to_box_not_transition_superiority=true
false_progression_not_bad_decision=true
coordinate_frame_is_validated_provider_truth=false
attack_direction_is_validated_truth=false
analysis_sentence_generated=false
event_instance_count=0
claim_allowed=false
sequence_truth=false
possession_truth=false
phase_truth=false
tactical_truth=false
canonical_event_count=UNKNOWN
production_release=false
```
