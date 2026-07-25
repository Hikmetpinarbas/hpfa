# Action Bundle Multi-Family Review Taxonomy Lite V1

## Amaç

`semantic_role_action_bundle_candidates_lite_v1` çıktısındaki `same_surface_multiple_action_families` kayıtlarını exact action-core düzeyinde sınıflandırır. Sınıflandırma, görünen family setinin neden review kuyruğunda olduğunu açıklar; event veya aksiyon truth üretmez.

## Authority

Tek ürün girdisi current HPFA action-bundle çıktısıdır. Donor repolar, Drive, Dropbox ve akademik kaynaklar yalnız yöntem desteğidir. ACTIVE_MATCH dışındaki hiçbir kaynak runtime truth değildir.

## Exact family-set registry

- `DUEL + TACKLE` → hierarchical subtype candidate
- `PASS + CROSS` → hierarchical subtype candidate
- `TURNOVER + CONTROL_ERROR` → hierarchical subtype candidate
- `PASS + RESTART` → restart-action coupling candidate

Registry dışındaki family setleri token tahminiyle yükseltilmez. İki aileli compound/same-time risk setleri ve üç veya daha fazla aileli core'lar review-required kalır.

## Core sınırı

Aynı core için şu alanların tamamı exact eşit olmalıdır:

- match-surface binding
- source role
- team identity candidate
- actor identity candidate
- period
- start/end
- x/y coordinate

Aynı zaman tek başına yeterli değildir. Player, team ve goalkeeper yüzeyleri birleştirilmez.

## Analyst-facing anlam

Çıktı, görünür family overlap yüzeylerini alt-tip adayı, restart coupling adayı, compound co-occurrence, same-time grouping riski ve complex review olarak ayırır. Bu ayrım analistin hangi yüzeylerin yakın semantik ilişki taşıdığını ve hangilerinin ayrı aksiyon olabileceği için inceleme istediğini görmesini sağlar.

## Claim boundary

```text
classification_is_event_truth=false
family_parent_is_validated_action=false
subtype_is_validated_action=false
restart_coupling_is_event_fusion=false
cross_role_fusion_allowed=false
event_instance_count=0
claim_allowed=false
sequence_truth=false
possession_truth=false
phase_truth=false
tactical_truth=false
canonical_event_count=UNKNOWN
production_release=false
```
