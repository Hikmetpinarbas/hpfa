# Coordinate Frame Precondition — Operator Research Prompts V1

Bu araştırmalar ürün veya ACTIVE_MATCH authority değildir. Sonuçlar yalnız `REFERENCE_ONLY / DONOR_SUPPORT` olarak değerlendirilir.

## Google Drive tarama promptu

HPFA Google Drive arşivinde coordinate frame, attack direction ve provider coordinate normalization ile ilgili bütün belgeleri tara.

Öncelikli terimler:

- coordinate frame
- attack direction
- attacking direction
- team-normalized coordinates
- possession-normalized coordinates
- provider-normalized pitch
- 105x68
- 100x100
- side switching
- half switching
- shot concentration
- goal kick location
- goalkeeper restart
- clearance location
- restart subtype
- SportsBase coordinate
- SportsBase goal kick
- axis integrity
- progression anchor
- final third entry
- box entry

Her bulgu için:

1. Dosya adı ve yolu
2. Kaynak rolü: governance, donor, archive, research veya implementation note
3. Provider veya veri formatı
4. Koordinat ölçeği
5. Absolute frame mi, team-attack-normalized frame mi?
6. Takım/periyot yönü nasıl belirleniyor?
7. Goal kick, shot ve clearance anchor kuralları var mı?
8. Minimum örneklem/eşik var mı?
9. Conflict ve fail-closed davranışı
10. HPFA'ya uyarlanabilir kısım
11. Kopyalanmaması gereken overclaim veya tracking bağımlılığı
12. Claim boundary

Hiçbir Drive kaydını ACTIVE_MATCH truth olarak sunma. Sonuçları ADAPT_NOT_COPY çerçevesinde karşılaştırmalı tabloyla ver.

## Dropbox tarama promptu

HPFA Dropbox arşivinde sequence, progression, coordinate normalization, restart subtype ve metric denominator çalışmalarını tara.

Öncelikli terimler:

- sequence window
- progression metric
- denominator
- final third support
- box entry support
- shot support
- goal kick
- restart
- clearance
- coordinate direction
- attack-normalized
- zone delta
- false progression
- outcome support
- metric gate
- semantic gate
- fail closed

Her bulgu için:

1. Dosya ve klasör
2. Modül veya contract ilişkisi
3. Input/output alanları
4. Numerator tanımı
5. Denominator tanımı
6. Direction/frame bağımlılığı
7. Outcome-support bağımlılığı
8. Sequence/possession/tactical truth riski
9. Kullanılabilir test veya negative-test fikri
10. HPFA current producer'larına bağlanma noktası
11. Reference-only veya donor-support kararı

Arşiv kayıtlarını current product veya runtime authority olarak yükseltme.
