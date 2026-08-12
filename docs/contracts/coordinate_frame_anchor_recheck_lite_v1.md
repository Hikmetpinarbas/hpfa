# Coordinate Frame Anchor Recheck Lite V1

## Amaç

`coordinate_frame_precondition_lite_v1` sonucunu, `provider_coordinate_attachment_semantics_lite_v1` tarafından açıkça admitted edilen reflection-clear goalkeeper `CROSS_OR_PASS_INTERCEPTION` event-action-location candidates ile yeniden değerlendirir.

Bu contract mevcut coordinate-frame producer'ını overwrite etmez. Downstream refinement/recheck üretir.

## Inputs

- `coordinate_frame_precondition_lite_v1`
- `provider_coordinate_attachment_semantics_lite_v1`

Her iki input aynı `match_surface_binding_id` üzerinde olmalıdır.

## Admission

Goalkeeper interception yalnız şu koşullarda primary counter-anchor candidate olabilir:

- attachment module `PASS`;
- `EVENT_ACTION_LOCATION_CANDIDATE_SUPPORTED`;
- `goalkeeper_interception_primary_direction_anchor_candidate_allowed=true`;
- `outcome_stratified_support_pooling_allowed=true`;
- `event_fusion_allowed=false`;
- attachment hard block/review yok;
- record-level candidate `EVENT_ACTION_LOCATION_CANDIDATE`;
- exact/overlapping same-coordinate object-action reflection count = 0;
- CSV/XML required aligned support;
- `validated_provider_semantics=false` korunur;
- minimum support = 2; bu current primary goal-side goal-kick minimumundan düşük değildir;
- normalized median `<=0.30` veya `>=0.70` goal-side bandında olmalıdır.

## Primary-family conflict policy

Her team-period için:

1. SHOT direction candidate gereklidir.
2. Resolved GK GOAL_KICK mevcutsa primary counter-anchor olarak korunur.
3. Admitted GK INTERCEPTION alternate/additional primary counter-anchor candidate olabilir.
4. Mevcut bütün resolved primary family yönleri aynı olmalıdır.
5. Herhangi bir conflict => `CONFLICTING_PRIMARY_ANCHORS_REVIEW_REQUIRED`.
6. Selective team-period progression opening yasaktır.

## Output

- baseline/recheck multi-anchor pass group counts
- goalkeeper interception primary-anchor group count
- goalkeeper interception gap-closure group count
- primary-anchor conflict count
- per-team-period recheck records
- `coordinate_frame_recheck_candidate`
- `progression_metric_recheck_allowed`

## Claim boundary

Bu modül aşağıdakileri doğrulamaz:

- validated provider coordinate truth
- goalkeeper physical-position truth
- tracking truth
- tactical truth
- progression truth
- line-break truth

Sabitler:

```text
coordinate_attachment_is_validated_provider_truth=false
coordinate_is_goalkeeper_physical_position_truth=false
coordinate_frame_is_validated_provider_truth=false
attack_direction_is_validated_truth=false
progression_truth=false
line_break_truth=false
canonical_event_count=UNKNOWN
production_release=false
```

`progression_metric_recheck_allowed=true` yalnız downstream progression metric recheck iznidir; progression truth değildir.

## Phone output

Yalnız:

- `/sdcard/Download/HPFA`
- `/storage/emulated/0/Download/HPFA`

Nested output reddedilir:

`nested_phone_output_directory_rejected`

## Match-agnostic

Product code maç, takım, tarih, turnuva, sample id veya sample row count hardcode etmez.

Mandatory test:

`test_no_sample_match_identity_leak`

## Release

PASS != release.
ACTIVE_MATCH evidence != production release.

`production_release=false`
