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

## ACTIVE_MATCH orchestration contract

Termux runner hazır telefon dosyalarının varlığını varsaymaz. Current exact head üzerinde şu sıra zorunludur:

```text
run_active_match_context_slicer_v1.sh
→ current-head upstream producer refresh
→ provider label semantics
→ semantic action bundles
→ selected action consequence
→ selected event consequence refresh
→ coordinate frame precondition
```

Runner:

- product repo origin, branch ve exact head değerini doğrular;
- ACTIVE_MATCH path'ini exact runtime authority ile karşılaştırır;
- tracked worktree kirliyse fail-closed olur;
- upstream producer'ları current branch/head üzerinde yeniler;
- required input dosyalarının aynı çalışma sırasında üretildiğini doğrular;
- eski veya stale telefon çıktısını current evidence olarak kabul etmez;
- legacy branch adına kilitli provider runner'ını current stacked branch üzerinde çağırmaz.

## Telefon çıktı sözleşmesi

Kullanıcıya görünür bütün dosyalar yalnız şu düz dizinlerden birine yazılır:

```text
/sdcard/Download/HPFA
/storage/emulated/0/Download/HPFA
```

Nested output yasaktır.

### Başarılı çalışma

```text
coordinate_frame_precondition_lite_v1.json
coordinate_frame_precondition_lite_v1.txt
coordinate_frame_precondition_analyst_audit_v1.txt
coordinate_frame_precondition_pytest_v1.txt
coordinate_frame_precondition_operator_state_v1.txt
coordinate_frame_precondition_active_match_bundle_manifest_v1.json
coordinate_frame_precondition_manifest_v1.sha256
coordinate_frame_precondition_active_match_bundle_v1.zip
```

Başarı ZIP'i current-run upstream lineage dosyalarını da flat olarak içerir:

```text
provider_label_value_semantics_lite_v1.json
semantic_role_action_bundle_candidates_lite_v1.json
selected_action_consequence_surface_lite_v1.json
selected_event_consequence_surface_lite_v1.json
```

### Başarısız çalışma

Upstream veya coordinate node fail-closed olduğunda yalnız terminal mesajı bırakılmaz. Runner şu tanı yüzeylerini telefon dizinine yazar:

```text
coordinate_frame_precondition_operator_state_v1.txt
coordinate_frame_precondition_failure_inventory_v1.txt
coordinate_frame_precondition_failure_bundle_v1.zip
```

Böylece operatör başarısız çalışmayı da indirilebilir ZIP olarak teslim edebilir. Failure bundle production veya ACTIVE_MATCH pass değildir; yalnız engineering diagnosis evidence'dır.

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
