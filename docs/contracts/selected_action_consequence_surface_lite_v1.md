# Selected Action Consequence Surface Lite V1.1

## Amaç

Bu sürüm görünür aksiyon-sonuç yüzeyini yalnız primary consequence sınıfı üretmekten çıkarıp, her kayıt için açık ve makine-okunur saha semantiği üretir. Null değerler artık **eksik**, **uygulanamaz** ve **görünür takip yok** durumlarını birbirine karıştırmaz.

```text
Selected Action Consequence Surface V1
→ Field Semantics Closure V1.1
→ explicit first layer / latency / retention / breakdown / displacement candidates
```

## Alan semantiği

### Actor identity applicability

- `APPLICABLE_BOUND_CANDIDATE`: player veya goalkeeper yüzeyinde actor candidate mevcut.
- `NOT_APPLICABLE_TEAM_SURFACE`: team reflection yüzeyinde actor alanı yapısal olarak uygulanamaz.
- `MISSING_REVIEW_REQUIRED`: actor beklenen yüzeyde identity candidate eksik.

Actor değeri uydurulmaz. `null` korunabilir ancak nedeni ayrı status alanında açıklanır.

### First visible follow-up

Her consequence kaydı şu alanları taşır:

- `first_visible_follow_up_status`
- `first_visible_follow_up_delta_status`
- `first_layer_team_state`
- `first_layer_node_ids`
- `first_layer_team_candidate_ids`
- `first_layer_actor_candidate_ids`
- `first_layer_source_roles`
- `first_layer_action_families`
- `first_follow_up_window_class`

Takım durumu:

```text
SAME_TEAM / OPPONENT / MIXED / UNKNOWN / NONE
```

`MIXED`, aynı timestamp katmanında hem anchor takım hem rakip yüzeyi görüldüğünü ve yapay sıralama yapılamadığını belirtir.

### Response latency

Same-team ve opponent görünür cevapları ayrı ayrı sınıflandırılır:

```text
WITHIN_5S
BETWEEN_5_AND_8S
BETWEEN_8_AND_12S
NO_VISIBLE_RESPONSE
UNKNOWN_REVIEW
```

Bu sınıflar yalnız timestamp farkıdır. Baskı yoğunluğu, reaksiyon hızı veya taktik başarı doğrusu değildir.

### Retention / handover

`retention_after_action_candidate`, ilk görünür zaman katmanındaki takım ilişkisini açıklar:

- same-team visible retention candidate;
- opponent visible handover candidate;
- mixed-team same-time review;
- no visible retention signal within 12 seconds;
- unknown review.

Bu alan possession truth üretmez.

### Turnover response

Yalnız `TURNOVER` veya `CONTROL_ERROR` anchor family için:

- opponent visible takeover;
- same-team recovery response;
- same-team visible response;
- mixed-team review;
- no visible response within 12 seconds;
- unknown review.

Diğer action family kayıtlarında değer `NOT_APPLICABLE` olur. Bu alan counterpress success veya player failure truth değildir.

### Raw coordinate displacement

İlk görünür zaman katmanında tek ve tutarlı coordinate candidate varsa:

- `raw_coordinate_delta_x_candidate`
- `raw_coordinate_delta_y_candidate`
- `raw_coordinate_displacement_candidate`
- `SHORT/MEDIUM/LONG_RAW_PROVIDER_DISPLACEMENT`

üretilir.

```text
coordinate_scale_status=UNVERIFIED_PROVIDER_SCALE
progression_interpretation_status=WAIT_ATTACK_DIRECTION_AND_COORDINATE_SCALE_CONTRACT
raw_coordinate_delta_is_progression_truth=false
```

Attack direction ve coordinate scale doğrulanmadan ileri/geri, progression, territorial gain veya zone gain yorumu yapılmaz.

### Pressure availability

```text
pressure_interpretation_status=UNAVAILABLE_EVENT_ONLY_NO_TRACKING_OR_EXPLICIT_PRESSURE_EVENT
```

Bu bir sessizlik değil, structured missing-data state'tir. Tracking, freeze-frame veya explicit pressure event olmadan pressure truth üretilmez.

## Analyst-facing kapasite

Top-level çıktı artık şunları sayar:

- actor applicability;
- first visible follow-up state;
- first-layer team state;
- first follow-up window;
- retention/handover candidate;
- same-team ve opponent response latency;
- turnover response;
- raw coordinate displacement availability/class;
- pressure ve progression interpretation status.

Böylece analist yalnız “sonraki aksiyon neydi?” değil, “ilk görünen cevap kimin yüzeyindeydi, ne kadar sürede geldi, retention mı handover mı adayıydı, turnover sonrasında hangi görünür cevap oluştu ve raw coordinate hareketi okunabilir mi?” sorularını sorgulayabilir.

## Donor sınırı

- current hpfa producer contract'ları ürün authority'sidir;
- Google Drive reaction-window ve RCPG belgeleri `REFERENCE_ONLY` rolündedir;
- tracking/pitch-control gerektiren değer modelleri uygulanmaz;
- Dropbox `CONSEQUENCE_MAPPING_RULES_B05.csv` method donorudur;
- yöntem `ADAPT_NOT_COPY`.

## Claim boundary

```text
selected_action_surface_is_canonical_event=false
consequence_candidate_is_causal_truth=false
continuation_candidate_is_possession_truth=false
retention_candidate_is_possession_truth=false
response_latency_class_is_pressure_truth=false
turnover_response_is_counterpress_success_truth=false
raw_coordinate_delta_is_progression_truth=false
window_is_sequence_truth=false
team_response_is_tactical_truth=false
event_instance_count=0
canonical_event_count=UNKNOWN
production_release=false
```
