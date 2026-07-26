# Cross-Role Relation Candidate Resolver Lite V1

## Amaç

Player veya goalkeeper primary-action surface ile team reflection surface arasındaki exact relation candidate'ları yeniden doğrular. Amaç, aynı action-family'nin farklı source-role yüzeylerinde tekrar görünmesini ilişki adayı olarak kaydetmek ve olası double-count yüzeyini işaretlemektir.

## Authority

Tek ürün girdileri:

- `semantic_role_action_bundle_candidates_lite_v1`
- `action_bundle_multi_family_review_taxonomy_lite_v1`

Donor repolar, Drive, Dropbox ve akademik kaynaklar yalnız yöntem desteğidir. Runtime truth yalnız `runtime/active_single_match/current` içindedir.

## Exact relation contract

Bir relation candidate için şu alanlar birebir eşleşmelidir:

- match-surface binding
- team identity candidate
- period
- start ve end time
- x ve y coordinate
- action family candidate

Ayrıca tam iki bundle bulunmalıdır. Biri TEAM surface, diğeri PLAYER veya GOALKEEPER surface olmalıdır. Primary tarafta actor identity candidate bulunmalı, team reflection tarafında actor identity bulunmamalıdır. Aynı zaman tek başına ilişki açamaz ve bir bundle iki relation candidate içinde kullanılamaz.

## Multi-family context integrity

Bundle review-required ise PR #194 taxonomy context'i zorunludur. Taxonomy kaydı yalnız bundle ID referansı taşıdığı için kabul edilmez. Her taxonomy kaydı, desteklediği review bundle'larla yeniden doğrulanır.

Zorunlu exact eşleşme alanları:

- match-surface binding
- source role
- team identity candidate
- actor identity candidate veya role-appropriate actor applicability
- period
- start ve end time
- x ve y coordinate
- coordinate evidence status
- exact family set

Bütün supporting bundle'lar `REVIEW_REQUIRED` olmalı, tek bir exact action-core paylaşmalı ve bundle family seti taxonomy `family_set` değeriyle birebir eşleşmelidir. Herhangi bir fark `FAIL_CLOSED` üretir.

`PASS_CANDIDATE_CLASSIFICATION` yalnız bu bütünlük kapısı geçildikten sonra relation context'ini clear candidate yapabilir. Unresolved taxonomy context relation'ı review-required bırakır. Hiçbir taxonomy sonucu action veya event truth üretmez.

## Double-count sınırı

Clear relation candidate için primary role surface yalnız `PRIMARY_COUNTING_SURFACE_CANDIDATE`, team surface ise `REFLECTION_ONLY_SURFACE_CANDIDATE` olarak işaretlenir. Bu, ancak ileride event admission geçerse uygulanabilecek counting-policy candidate'ıdır. Bu düğüm count üretmez, kayıt silmez ve final suppression yapmaz.

## Claim boundary

```text
relation_candidate_is_event_truth=false
reflection_equivalence_truth=false
double_count_suppression_is_final=false
count_value_output_allowed=false
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
