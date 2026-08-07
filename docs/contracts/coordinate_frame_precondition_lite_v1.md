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

REFERENCE_ONLY veya DONOR_SUPPORT materyalindeki `PASS`, `RELEASE_CANDIDATE`, `VERIFIED_GAIN` ya da benzeri eski durumlar current HPFA product status'üne miras bırakılamaz. Current product status yalnız current-head engineering evidence ve ACTIVE_MATCH runtime evidence ile yükseltilebilir.

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

Clearance volume hiçbir eşik veya çoğunluk kuralıyla primary direction anchor'a terfi ettirilemez. Bu rol değişikliği yeni contract ve yeni evidence gerektirir.

## Admission

`progression_metric_recheck_allowed=true` yalnız şu durumda üretilebilir:

1. scale `PROVIDER_105X68_SCALE_CANDIDATE`;
2. bounds `PASS_CANDIDATE_BOUNDS`;
3. selected-event tarafından beklenen her team-period grubu için shot + goalkeeper goal-kick primary anchor agreement;
4. primary-anchor conflict yok;
5. input binding ve inventory gate'leri geçer.

Admission maç içi simetriyi korur: beklenen team-period gruplarının yalnız bir alt kümesi resolved ise selective team-level progression admission açılamaz. `progression_metric_recheck_allowed` match-level fail-closed kalır.

Bu alan progression metriğinin otomatik PASS olduğu anlamına gelmez. Sonraki metric-recheck node'u numerator, denominator, outcome support, attachment semantics ve definition alignment sözleşmelerini ayrıca doğrulamalıdır.

## Donor-informed progression guardrails

Aşağıdaki kurallar yalnız `REFERENCE_ONLY / DONOR_SUPPORT` materyalinden HPFA contract'ına adapte edilmiştir; donor statüleri runtime truth değildir:

- progression bir evidence surface'tir; dominance veya tactical truth değildir;
- mevcut progression producer'ları upstream evidence olarak yeniden kullanılabilir, fakat dirty binding veya claim shortcut yapılamaz;
- attachment semantics ayrı bir risk yüzeyidir ve coordinate frame çözülse bile ayrıca doğrulanmalıdır;
- PDF veya archive runtime authority olamaz;
- ACTIVE_MATCH proof bypass edilemez;
- historical donor `PASS` veya `RELEASE_CANDIDATE` current product release kararı değildir;
- progression recheck coordinate-frame admission sonrasında da numerator, denominator, outcome support ve definition alignment gate'lerine tabidir.

Bu kurallar mevcut ürün davranışını genişletmek için değil, yanlış shortcut'ları engellemek için kullanılır.

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
→ ACTIVE_MATCH provenance audit
→ G07/G16 + aggregate dependency audit
```

Runner:

- product repo origin, branch ve exact head değerini doğrular;
- ACTIVE_MATCH path'ini exact runtime authority ile karşılaştırır;
- tracked worktree kirliyse fail-closed olur;
- upstream producer'ları current branch/head üzerinde yeniler;
- required input dosyalarının aynı çalışma sırasında üretildiğini doğrular;
- eski veya stale telefon çıktısını current evidence olarak kabul etmez;
- legacy branch adına kilitli provider runner'ını current stacked branch üzerinde çağırmaz;
- generic producer'ın runtime-neutral output'unu yalnız exact ACTIVE_MATCH execution tamamlandıktan sonra runtime provenance ile yükseltir;
- current-run G01–G18 rollup ile aggregate-definition-alignment sonucunu dependency sidecar'a taşır, fakat bunları coordinate-frame veya metric truth'a yükseltmez.

### Runtime evidence elevation

Generic producer output'u fixture, CI veya standalone execution bağlamında `runtime_evidence_status=NOT_EVALUATED` kalabilir. Bu beklenen davranıştır.

Yalnız ACTIVE_MATCH runner şu koşullar sağlandığında ana coordinate JSON'una exact-run provenance yazar:

- runtime authority exact eşleşir;
- current branch/head doğrulanır;
- coordinate execution `run_rc` değeri 0 veya 1'dir;
- hard block yoktur.

Bu durumda:

- module sonucu `PASS` ve `progression_metric_recheck_allowed=true` ise `ACTIVE_MATCH_EVIDENCE_PASS`;
- execution tamamlanmış fakat module `REVIEW_REQUIRED` veya progression admission kapalı ise `ACTIVE_MATCH_EXECUTION_COMPLETED_REVIEW_REQUIRED`;
- authority/execution contract tamamlanmamışsa `ACTIVE_MATCH_EXECUTION_NOT_COMPLETED`.

ACTIVE_MATCH evidence status release status değildir. `production_release=false` korunur.

## G07 / G16 dependency visibility

Coordinate runner current-run şu iki upstream review yüzeyini ayrıca görünür kılar:

- `G07`: coordinate surface / coordinate-missing nucleus evidence;
- `G16`: aggregate derivation dependency gate.

Bunlara ek olarak `aggregate_definition_alignment_lite_v1.json` içindeki review hits dependency audit sidecar'a taşınır.

Bu sidecar'ın amacı açıklanabilirliktir. G07/G16 veya aggregate review evidence:

- coordinate frame admission'ı override edemez;
- missing primary direction anchor'ı tamamlayamaz;
- progression metric truth oluşturamaz;
- canonical event truth oluşturamaz.

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
coordinate_frame_precondition_active_match_v1.txt
coordinate_frame_precondition_runtime_audit_v1.txt
coordinate_frame_precondition_dependency_audit_v1.json
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
g01_g18_data_quality_rollup_v1.json
aggregate_definition_alignment_lite_v1.json
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
coordinate_frame_precondition_active_match_v1.txt
coordinate_frame_precondition_runtime_audit_v1.txt
coordinate_frame_precondition_dependency_audit_v1.json
```
