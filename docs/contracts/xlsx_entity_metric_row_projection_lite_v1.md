# XLSX Entity-Metric Row Projection Lite V1

## Amaç

`xlsx_surface_reader_lite_v1` tarafından kabul edilmiş görünür XLSX yüzeyindeki aynı satıra ait identity candidate alanları ile metric hücrelerini provenance korunarak birlikte projekte eder.

Bu modül yeni bir XLSX reader değildir. Ham dosyayı yalnız mevcut inventory + XLSX audit kararına bağlı olarak tekrar açar ve exact SHA/header binding sağlanmadan row projection üretmez.

```text
multiformat_file_inventory_lite_v1
→ xlsx_surface_reader_lite_v1
→ xlsx_entity_metric_row_projection_lite_v1
→ aggregate_derivation_evidence_reconciliation_lite_v1
→ G16 recheck admission
```

## Neden gerekli?

XLSX surface audit `column_profiles[].example_values` ve `identity_binding[].example_candidates` üretir; ancak bu örnekler unique/truncated profile evidence'tır. Bir metric örneğini belirli bir oyuncu/kaleci satırıyla eşleştirmek için kullanılamaz.

Bu node yalnız **aynı kaynak satırında birlikte gözlenen** hücreleri bağlar.

## Admission

Zorunlu koşullar:

- input root mevcut olmalı;
- input XLSX audit `xlsx_surface_reader_lite_v1` olmalı;
- XLSX audit `FAIL_CLOSED` olmamalı;
- audit file_id inventory'de bulunmalı;
- inventory/audit relative path aynı olmalı;
- inventory/audit SHA-256 aynı olmalı;
- raw XLSX exact SHA-256 inventory ile aynı olmalı;
- sheet audit'e göre görünür olmalı;
- header row ve raw headers audit ile birebir uyuşmalı.

Duplicate normalized metric key varsa dictionary overwrite yapılmaz; sheet `REVIEW_REQUIRED` kalır ve row projection açılmaz.

## Formula ve missing davranışı

- Formula evaluate edilmez.
- Cached value varsa row-level surface value olarak korunabilir.
- Formula var fakat cached value yoksa metric `NOT_ADMITTED_FORMULA_CACHE_MISSING` olur.
- Numeric `0` observed value'dır, missing değildir.
- `-`, `N/A` ve benzeri string yüzeyler numeric zero'ya çevrilmez.

## Identity

`player`, `team`, `position`, `minutes`, `shirt_number` yalnız audit tarafından verilmiş `identity_role_candidate` üzerinden aynı satırda candidate olarak taşınır.

```text
validated_identity=false
```

Global player/team identity veya match truth üretilmez.

## Row projection

Her admitted visible row için:

```text
row_projection_id
file_id
relative_path
source_sha256
source_role
sheet_name
sheet_state
header_row_index
source_row_number
match_surface_binding_id
identity_candidates
metric_values
row_surface_claim_ceiling
validated_identity=false
canonical_event_count=UNKNOWN
production_release=false
```

Her metric hücresi raw label/value, value kind, number format, percent-header candidate, formula/cache ve admission state taşır.

## Runtime evidence

`--active-match-execution` kullanıldığında input root ile runtime authority aynı olmalı ve path `runtime/active_single_match/current` ile bitmelidir.

Ana output kendi runtime durumunu taşır:

```text
ACTIVE_MATCH_EXECUTION_COMPLETED_PASS
ACTIVE_MATCH_EXECUTION_COMPLETED_REVIEW_REQUIRED
ACTIVE_MATCH_EXECUTION_COMPLETED_FAIL_CLOSED
```

CI veya fixture sonucu ACTIVE_MATCH evidence değildir.

## Analyst-facing anlam

Güvenli ifade:

> Görünür XLSX satırında aynı satıra ait identity candidate ve metric hücreleri birlikte gözlendi.

Bu ifade şunları söylemez:

- oyuncu/takım kimliği doğrulandı;
- aggregate provider tanımı doğrulandı;
- metric truth üretildi;
- iki format bağımsız doğrulama sağladı;
- karşılaştırma/release yapılabilir.

## Claim boundary

```text
row_projection_is_canonical_event=false
validated_player_identity=false
validated_team_identity=false
aggregate_definition_truth=false
metric_truth=false
comparison_allowed=false
claim_allowed=false
canonical_event_count=UNKNOWN
production_release=false
```

## Phone output

User-visible Termux output yalnız:

```text
/sdcard/Download/HPFA
/storage/emulated/0/Download/HPFA
```

Nested output reddedilir:

```text
nested_phone_output_directory_rejected
```
