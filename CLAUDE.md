# HPFA — Claude Çalışma Kuralları

Bu dosya, Claude Code'un bu repo'da her oturum başında otomatik okuduğu kalıcı çalışma
kurallarını taşır. Amaç: operatöre (Hikmet Pınarbaş) teslim edilen çıktıların teslim
edilebilir formatta kalmasını garanti etmek.

## STANDART KURAL — Yanıt Uzunluğu Tavanı

**Operatöre teslim edilen her yanıt/rapor/analiz metni 20.000 karakteri (harf sayısı,
boşluklar dahil) AŞAMAZ.**

Gerekçe: Operatörün bu çıktıyı teslim alabileceği maksimum harf sayısı budur.

Uygulama:
- Bu sınır, sohbet içi doğrudan yanıtlar için geçerlidir (ör. HPFA-RD-XXX serisi
  araştırma/denetim raporları, mimari denetim çıktıları, gap-analiz raporları).
- Uzun/derin görevlerde (çok başlıklı audit, çok bölümlü rapor) içerik bu tavana
  sığacak şekilde yoğunlaştırılmalı: gereksiz tekrar, dekoratif başlık, fazladan örnek
  budanır; kanıt yoğunluğu (file:line, somut sayı) korunur.
- Eğer görev doğası gereği 20.000 karakterin çok üzerinde detay gerektiriyorsa,
  çıktı EXECUTIVE (sohbette, ≤20.000 karakter) + FULL (ayrı bir dosya/artifact olarak)
  şeklinde ikiye bölünür. Sohbete giden mesaj tek başına asla 20.000 karakteri geçmez.
- Bu tavan, kod/dosya içine yazılan teknik çıktılar (JSON, kontrat, test) için değil,
  Claude'un operatöre ürettiği doğrudan metin teslimatları için geçerlidir.

Bu kural, aksi operatör tarafından açıkça değiştirilene kadar kalıcıdır.
