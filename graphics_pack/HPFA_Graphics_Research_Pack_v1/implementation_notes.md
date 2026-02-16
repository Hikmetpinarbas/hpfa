# HPFA Implementation Notes — Graphics Pack v1

Bu notlar, **event tabanlı veri** ile üretilebilecek grafiklerin *doğru* ve *yanıltıcı olmayan* şekilde üretilmesi içindir.

## 0) SSOT ve Dosya Sözleşmesi
- SSOT: `canonical_*.jsonl` (hpfa_ingest_v1 çıktıları)
- Her record için minimum alanlar:
  - `match_id, stream, t_start, t_end, team_id, player_id, action, x, y`
- `UNKNOWN_TEAM` veya `player_id=None` oranı, çekirdek grafiklerde %1’i geçerse **hard-fail**.

## 1) Saha Ölçeği ve Normalize
- Kaynak saha ölçeği: **105×68** (metre).
- Bazı feed’ler 100×50 normalize edebilir. Çizim modülü **tek standarda** oturmalı:
  - İç hesap: 105×68
  - Opsiyonel render: 100×50 (sadece görselleştirme ölçeği)

### Ölçek dönüşümü (105×68 → 100×50)
- x' = x * (100/105)
- y' = y * (50/68)

## 2) Yön Problemi (Half flip) — Altın Kural
Event datası “takımın gerçek hücum yönünü” garanti etmez.
Bu yüzden:
- İKİNCİ YARI için takım bazında `flip_second_half` kararı üret
- Karar metodu (robust):
  - m1 = median(x) first half, m2 = median(x) second half
  - Flip adayı: second half x' = 105 - x
  - Eğer |m1 - m2| küçük kalıyorsa ve GK sanity check bozuluyorsa flip uygula.

### Sanity Check (zorunlu)
- GK aksiyonlarının çoğu kendi ceza alanına yakın olmalı (x ~ 0–20 ya da 85–105 takım yönüne göre)
- Şutların çoğu rakip ceza alanına yakın kümelenmeli
- Bu bozuluyorsa: yön/scale bozuk demektir.

## 3) “Pozisyon” Yanılgısı
Event verisi tracking değildir.
Bu yüzden üretilen haritalar:
- **median action location** (aksiyon lokasyonu) = oyuncunun “konumlanması” değil.
Grafik başlıklarında bu ifade **zorunlu**.

## 4) 3. Takım (UNKNOWN_TEAM) Neden Çıkar?
Nedenler:
- `team` alanı boş/uyumsuz
- farklı dil/encoding (“Çaykur” vs “Caykur”)
- team_id parse map eksik

Çözüm:
- `team_id` parse sözlüğü (canonical map) version’lanır.
- UNKNOWN_TEAM > %1 ise rapor üret ama grafik üretme (fail fast).

## 5) Aşırı Merkez Kümelenmesi (midfield inflation)
Sebep:
- Her aksiyonun doğal olarak top çevresinde toplanması
- Set oyunu + pas yoğunluğu

Çözümler:
- Grafik filtreleri:
  - Sadece belirli action setleri (pass+def+shot)
  - Faz bazlı facet (F1/F2/F4 ayrı)
  - Yoğunluk yerine “entry/shot/turnover” odaklı layer

## 6) Üç CSV / Üç XML meselesi (pairing)
Aynı maçın birden fazla export’u olabilir.
- Pairing kuralı: (start,end,code) örnek kesişim maksimize
- Ancak XML segment/annotation olabilir → 0 match “normal” olabilir.
Bu durumda:
- XML’i “video tag stream” olarak ayrı kaydet, event ile zorla hizalama yapma.

## 7) Minimum Grafik Seti (yayın-ready)
Eğer sadece 7 grafik çıkaracaksan:
1) Phase distribution
2) Events per minute
3) Momentum panel
4) Shot map
5) Turnover map (own-half)
6) Regain map + regain height
7) Possession chain funnel

## 8) Çalıştırma (Termux)
- Her match için:
  - `~/hpfa/data/matches/<match_id>/in/`
  - `~/hpfa/out/<match_id>/`
- Sonra grafik üreticiler `~/hpfa/out/<match_id>/canonical_*.jsonl` üzerinden çalışır.
