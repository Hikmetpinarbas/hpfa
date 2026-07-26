# Cross-Role Relation Review Profiler Lite V1

## Amaç

`cross_role_relation_candidate_resolver_lite_v1` çıktısındaki `REVIEW_REQUIRED` ilişkileri çözmeden, saymadan veya event olarak yükseltmeden neden ailelerine ayırır.

Bu düğüm şu soruya cevap verir:

> Hangi oyuncu–takım yansıma ilişkileri neden hâlâ belirsiz ve sıradaki geliştirme hangi ilişki ailesine odaklanmalıdır?

## Çıktı yüzeyleri

- review reason dağılımı;
- action-family dağılımı;
- PLAYER+TEAM ve GOALKEEPER+TEAM rol dağılımı;
- taxonomy context var/yok dağılımı;
- family × review-reason matrisi;
- source relation lineage taşıyan review profilleri.

## Claim boundary

Bu düğüm:

- ilişki çözmez;
- double-count suppression kararı vermez;
- event üretmez;
- canonical event sayısı üretmez;
- sequence, possession, phase veya tactical truth üretmez;
- metric veya analyst claim açmaz.

```text
profile_resolves_relations=false
count_value_output_allowed=false
event_instance_count=0
canonical_event_count=UNKNOWN
production_release=false
```

## Güvenli analist anlamı

> Görünür cross-role relation review yüzeyi neden, aksiyon ailesi ve rol çifti bazında profillendi. Bu profil hangi belirsizlik ailesinin önce ele alınması gerektiğini gösterir; fiziksel aksiyon, final double-count kararı veya canonical event truth üretmez.
