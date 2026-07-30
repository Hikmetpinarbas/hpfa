# Event-derived Phase State Lite V1

## Amaç

Zaman, sıra, takım, action-family ve yön-normalize edilmiş zone kanıtını kullanarak
görünür action sequence adaylarını faz segmentlerine ayırır.

Bu modül “event verisinden faz üretilemez” varsayımını reddeder. Doğru sınır şudur:
faz durumu event kanıtından türetilebilir; bu durum tek başına taktik niyet, off-ball
yerleşim, pres, fiziksel yorgunluk veya tracking gerçeği değildir.

## Durum makinesi

- restart
- hücum geçişi
- birinci bölge oyun kurulumu
- orta bölge ilerlemesi
- son üçte bir erişimi
- ceza alanı erişimi
- sonlandırma
- açık oyun bölgesi çözümlenemedi

Tek event bütün fazı belirlemez. Consecutive anchor’lar aynı sınıfta birleştirilir.
Geçiş başlangıcı yalnız regain-to-visible-continuation sinyali varsa açılır; on saniyelik
sözleşme penceresi ve iki görünür anchor hysteresis’i kullanılır.

## Cross-team geçiş sınırı

Takım değişimi, kaybeden takımın savunma geçişi davranışını gözlenmiş kabul etmez.
Transition context window yalnız upstream sequence modülünün açık
`VISIBLE_TEAM_HANDOVER_CANDIDATE` boundary kaydı varsa üretilir. Zaman sırasındaki
iki farklı takım sequence'inin komşuluğu tek başına handover kanıtı sayılmaz; arada
mixed-team, context-only, restart veya time-gap sınırı bulunabilir.

Boundary'nin önceki/sonraki sequence referansı, period, takım ve boundary zamanı
doğrulanır. Eksik veya çelişkili kayıt fail-closed olur. Pencere yeni takımın görünür
sequence başlangıcında açılır ve en fazla on saniye sürer:

`min(next_sequence_end, next_sequence_start + 10s)`

Kaybeden takımın off-ball tepkisi ancak daha sonra video/tracking ile doğrulanabilir.

## Kimlik ve uzlaştırma kapıları

Duplicate selected-action node kimliği veya duplicate selected-event anchor kimliği
sessizce son kayıtla ezilmez; fail-closed olur. Sequence ve boundary için ilan edilen
sayılarla gerçek liste uzunlukları uyuşmalıdır.

## Claim ceiling

Mevcut upstream yüzeyler candidate düzeyinde olduğu için `phase_truth=false` kalır.
Bu, fazın üretilemediği anlamına gelmez; üretilen segmentin doğrulanmış canonical-event
truth seviyesine henüz yükselmediği anlamına gelir.

Status:

`SPEC_AND_TESTED_IMPLEMENTATION / ACTIVE_MATCH_NOT_EVALUATED / NOT_PRODUCTION`
