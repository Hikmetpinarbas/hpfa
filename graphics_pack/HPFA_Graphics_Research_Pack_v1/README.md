# HPFA Graphics Research Pack — v1

Bu paket, HPFA için **event tabanlı** (tracking gerektirmeyen) yüksek değerli grafik kataloğudur.

## İçerik
- `graphics_catalog.json` — 40 grafik için: veri sözleşmesi, matematik, tuzaklar, doğrulama kapıları, alternatifler
- `implementation_notes.md` — saha ölçeği (105×68), flip, UNKNOWN_TEAM, clustering ve QC protokolleri

## Kullanım
1) Önce ingest:
   - `hpfa_ingest_v1.py --match-id ... --in-dir ... --out-dir ...`
2) Sonra grafik üretici modüller:
   - Kataloğu referans alarak tek tek grafik fonksiyonları implement et.
3) Her maçta önce **G40 Quality Gates** koş.
