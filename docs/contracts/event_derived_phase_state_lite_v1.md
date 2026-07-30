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

Zone sınıflandırmasında reviewed `anchor_zone_rank_candidate` birincil girdidir.
Metin fallback'i kullanıldığında özel `FINAL_THIRD_*` etiketi generic `BOX` token
kontrolünden önce değerlendirilir. Böylece
`FINAL_THIRD_OUTSIDE_BOX_CANDIDATE`, yalnız adında `BOX` geçtiği için ceza alanı
erişimi olarak yanlış sınıflandırılamaz.

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

Sonraki sequence yalnız tek zaman anchor'ı içeriyor ve pozitif zaman aralığı
üretmiyorsa kayıt “window” olarak sayılmaz. Kanıt kaybolmasın diye ayrı
`CROSS_TEAM_HANDOVER_ANCHOR_ONLY_CANDIDATE` kaydı olarak korunur.

Kaybeden takımın off-ball tepkisi ancak daha sonra video/tracking ile doğrulanabilir.

Analist çıktısı; unresolved, review-required, warning ve zero-span segment sayılarını
ayrı verir. Bu kategoriler birbirinin yerine kullanılmaz.

## Kimlik ve uzlaştırma kapıları

Duplicate selected-action node kimliği veya duplicate selected-event anchor kimliği
sessizce son kayıtla ezilmez; fail-closed olur. Sequence ve boundary için ilan edilen
sayılarla gerçek liste uzunlukları uyuşmalıdır.

## Claim ceiling

Mevcut upstream yüzeyler candidate düzeyinde olduğu için `phase_truth=false` kalır.
Bu, fazın üretilemediği anlamına gelmez; üretilen segmentin doğrulanmış canonical-event
truth seviyesine henüz yükselmediği anlamına gelir.

Status:

`ACTIVE_MATCH_EXECUTION_COMPLETED_REVIEW_REQUIRED / NOT_PRODUCTION`
