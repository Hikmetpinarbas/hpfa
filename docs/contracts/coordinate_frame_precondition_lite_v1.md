# Coordinate Frame Precondition Lite V1

## Amaç

Bu düğüm, mevcut HPFA üreticilerini yeniden yazmadan üç ayrı görünür kanıt yüzeyini bir coordinate-frame precondition altında uzlaştırır:

```text
provider_label_value_semantics_lite_v1
+ semantic_role_action_bundle_candidates_lite_v1
+ selected_event_consequence_surface_lite_v1
→ coordinate_frame_precondition_lite_v1
```

Düğüm coordinate-frame truth üretmez. Yalnız altı bloklu progression metriğinin yeniden değerlendirilmeye alınıp alınamayacağını belirleyen candidate-only bir admission gate üretir.

## Kaynak rolleri

- current hpfa producer'ları: `PRODUCT_PRODUCER`
- `runtime/active_single_match/current`: `ACTIVE_MATCH_AUTHORITY`
- Drive, Dropbox, donor repo ve akademik kaynaklar: `REFERENCE_ONLY / DONOR_SUPPORT`
- yöntem: `ADAPT_NOT_COPY`

## Primary anchor aileleri

### 1. Shot concentration

Selected Event Consequence Surface içindeki team-period shot concentration candidate'ı kullanılır.

Zorunlu koşullar:

- en az üç görünür shot-support node;
- `PASS_SHOT_CONCENTRATION_CANDIDATE`;
- resolved high-x veya low-x direction candidate.

### 2. Goalkeeper goal-kick start

Goal-kick subtype token tahminiyle bulunmaz. Zorunlu lineage:

```text
provider_label_record
  mapping_status = exact reviewed
  restart_type_candidate = GOAL_KICK
  source_role = GOALKEEPER_SURFACE_CANDIDATE
→ exact normalized label
→ action_bundle.normalized_labels
→ goalkeeper action bundle coordinate
```

Team reflection goal-kick kayıtları başlangıç noktası anchor'ı olarak kabul edilmez.

## Supporting anchor

Clearance dağılımı yalnız counter-support'tur. Clearance tek başına direction gate açamaz. Shot ve goalkeeper goal-kick primary anchor'ları uzlaştıktan sonra yalnız confidence desteği sağlar veya conflict review üretir.

## Admission

`progression_metric_recheck_allowed=true` yalnız şu durumda üretilebilir:

1. scale `PROVIDER_105X68_SCALE_CANDIDATE`;
2. bounds `PASS_CANDIDATE_BOUNDS`;
3. selected-event tarafından beklenen her team-period grubu için shot + goalkeeper goal-kick primary anchor agreement;
4. primary-anchor conflict yok;
5. input binding ve inventory gate'leri geçer.

Bu alan progression metriğinin otomatik PASS olduğu anlamına gelmez. Sonraki metric-recheck node'u numerator, denominator, outcome support ve definition alignment sözleşmelerini ayrıca doğrulamalıdır.

## Claim boundary

```text
coordinate_frame_is_validated_provider_truth=false
attack_direction_is_validated_truth=false
clearance_is_primary_direction_anchor=false
progression_truth=false
line_break_truth=false
sequence_truth=false
possession_truth=false
phase_truth=false
tactical_truth=false
canonical_event_count=UNKNOWN
production_release=false
```

## Çıktılar

```text
coordinate_frame_precondition_lite_v1.json
coordinate_frame_precondition_lite_v1.txt
coordinate_frame_precondition_analyst_audit_v1.txt
```
