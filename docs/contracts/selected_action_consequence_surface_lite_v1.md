# Selected Action Consequence Surface Lite V1

## Amaç

Bu düğüm HPFA'nın ilk doğrudan futbol zekâsı kapasite katmanıdır. Görünür action-bundle yüzeylerini seçer, takım reflection tekrarlarını ayırır ve her seçilmiş aksiyonu sonraki görünür aksiyon katmanlarına bağlar.

```text
Action Bundle Candidates
+ Multi-Family Review Taxonomy
+ Cross-Role Relation Resolver
+ Evidence Atoms
→ Selected Action Consequence Surface Lite V1
```

## Yeni analitik kapasite

Modül şu sorular için görünür kanıt yüzeyi üretir:

- aksiyondan sonra aynı takım devam etti mi;
- rakip görünür aksiyon yüzeyini devraldı mı;
- sonraki kısa pencerede şut görüldü mü;
- restart veya reset yüzeyi oluştu mu;
- turnover/control error sonrasında recovery/interception cevabı görüldü mü;
- recovery/interception aynı takım devamına bağlandı mı;
- aksiyonun exact yüzeyinde terminal veya derived-consequence desteği var mı;
- 5, 8 ve 12 saniyelik pencerelerde görünür follow-up yoğunluğu neydi.

## Seçim politikası

Her action-bundle tam olarak bir duruma ayrılır:

1. `SELECTED_ACTION_SURFACE_CANDIDATE`
2. `SUPPRESSED_TEAM_REFLECTION_CANDIDATE`
3. `QUARANTINED_UNRESOLVED_ACTION_SURFACE`

Clear cross-role relation içinde primary player/goalkeeper yüzeyi seçilir, team reflection yüzeyi ayrı tutulur. Unresolved cross-role relation içindeki iki yüzey de karantinaya alınır. Standalone PASS bundle seçilir. Review-required bundle yalnız taxonomy `PASS_CANDIDATE_CLASSIFICATION` veriyorsa seçilir.

Bu ayrım kayıt silmez ve final double-count suppression yapmaz.

## Same-time multi-family davranışı

Aynı source role, team, actor, period, time ve coordinate çekirdeğinde bulunan birden fazla family aynı `selected_action_node` içinde gruplanır. Aynı zamanlı family kayıtları birbirinin devamı sayılmaz.

## Consequence window

Her selected action node için yalnız aynı period içindeki, strict-positive time farkına sahip sonraki görünür node'lar incelenir.

```text
windows = 5s / 8s / 12s
maximum_follow_up_time_layers = 3
same_time_link_allowed = false
negative_time_link_allowed = false
cross_period_link_allowed = false
```

Time layer, aynı timestamp'teki bir veya daha fazla node'u birlikte taşır. Böylece aynı anda görülen farklı oyuncu veya family yüzeyleri yapay sıraya sokulmaz.

## Support atom attachment

Yalnız exact source role + period + start/end + coordinate eşleşmesiyle şu atomlar destek olarak bağlanır:

- `DERIVED_CONSEQUENCE_ATOM`
- `TERMINAL_OUTCOME_ATOM`

Cross-role support atom fusion yapılmaz.

## Üretilen profiller

- team candidate + action family consequence profile;
- actor candidate + action family consequence profile;
- consequence class dağılımı;
- 5/8/12 saniyelik visible follow-up coverage;
- selected, suppressed ve quarantined yüzey dökümü.

## Donor sınırı

- hpfa current producer contract'ları ürün authority'sidir.
- HP-Motor sequence ordering yalnız donor support'tur.
- HP-Engine gap/restart/team-change segmentation yalnız donor support'tur.
- Google Drive action-vs-reaction ve continuation-quality belgeleri reference-only'dir.
- Dropbox consequence mapping kuralları method donorudur.

Yöntem: `ADAPT_NOT_COPY`.

## Claim boundary

```text
selected_action_surface_is_canonical_event=false
consequence_candidate_is_causal_truth=false
continuation_candidate_is_possession_truth=false
window_is_sequence_truth=false
team_response_is_tactical_truth=false
event_instance_count=0
claim_allowed=false
sequence_truth=false
possession_truth=false
phase_truth=false
tactical_truth=false
canonical_event_count=UNKNOWN
production_release=false
```
