# Phase-Aware Sequence Refinement Lite V1

## Amaç

Event-derived faz segmentlerinde görülen kısa A–B–A salınımlarını ayırır. Kaynak
faz segmentlerini değiştirmez; her segment için koruma, iyileştirme adayı veya
yetersiz kanıt kararı üretir.

## Futbol mantığı

Aynı görünür sequence içinde A fazından B fazına, hemen ardından yeniden A fazına
geçiş her zaman veri gürültüsü değildir. Restart, hücum geçişi ve sonlandırma gibi
tek aksiyonluk kısa fazlar futbol anlamı taşıyabilir ve korunur.

İyileştirme adayı yalnız şu dar durumda üretilir:

- üç segment aynı görünür sequence içindedir;
- ilk ve üçüncü faz aynıdır, orta faz farklıdır;
- orta faz tek görünür anchor ve sıfır zaman aralığı taşır;
- iki yan segmentte en az ikişer görünür anchor vardır;
- üçlü review-bounded değildir;
- orta faz restart, hücum geçişi veya sonlandırma değildir.

Bu koşullar karşılansa bile otomatik birleştirme yapılmaz.

## Kararlar

- `RETAIN_NO_A_B_A_OSCILLATION`
- `RETAIN_PROTECTED_PHASE_CHANGE`
- `RETAIN_SUPPORTED_PHASE_CHANGE`
- `REFINEMENT_CANDIDATE_SINGLE_ANCHOR_OSCILLATION`
- `INSUFFICIENT_ANCHOR_REVIEW_REQUIRED`

## Analist açısından anlam

Çıktı, sequence’in nerede gerçekten faz değiştirmiş göründüğünü; nerede tek
aksiyonluk etiket sıçraması bulunduğunu; nerede kanıtın karar vermeye yetmediğini
ayrı gösterir. Kaynak segmentlerin hiçbiri silinmez.

## Sınır

Bu yüzey possession, taktik niyet, off-ball yapı veya doğrulanmış sequence gerçeği
üretmez. `canonical_event_count=UNKNOWN` ve `production_release=false` korunur.

Status: `SPEC_AND_TESTED_IMPLEMENTATION / ACTIVE_MATCH_NOT_EVALUATED / NOT_PRODUCTION`
