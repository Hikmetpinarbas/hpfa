HP-Motor Termux Bootstrap (SAFE, event-only, NO-GUESSING)
========================================================

Bu paket Termux'ta *sıfırdan* çalıştırmak için tasarlanmıştır.
- Gereken minimum: python
- Opsiyonel: matplotlib (tempo.png için)

KURULUM (Termux içinde)
-----------------------
1) Termux'u aç
2) Depo güncelle:
   pkg update -y && pkg upgrade -y

3) Depolama izni (isteğe bağlı ama tavsiye):
   termux-setup-storage

4) Gerekli paketler:
   pkg install -y python zip unzip

5) (Opsiyonel) Matplotlib istiyorsan (zor olabilir):
   pip install --upgrade pip
   pip install matplotlib

ÇALIŞTIRMA
----------
Bu zip'i telefona indirip aç:
- Önerilen yer: /sdcard/Download/

Termux'ta:
  cd ~
  mkdir -p hp_motor && cd hp_motor
  cp /sdcard/Download/hp_motor_termux_bootstrap.zip .
  unzip hp_motor_termux_bootstrap.zip

Maç paketi klasörünü oluştur:
  mkdir -p MATCH_PACK/out
  cp /sdcard/Download/events.csv MATCH_PACK/events.csv
  # (opsiyonel) alias_map.json ve context_vector.json kopyala

Koş:
  python STEP12_PHASE_TAGGER_MVP.py --match-pack MATCH_PACK
  python STEP13_TEMPO_MOMENTS.py --match-pack MATCH_PACK
  python STEP14_BRIEF_V2_RENDER.py --match-pack MATCH_PACK

Çıktılar:
  MATCH_PACK/out/

ÖNEMLİ: Bu paket hiç bir şey silmez. rm -rf gibi komutlar içermez.

========================
REPORTS RELEASE CHECKLIST
========================

One-command release (recommended):
  ./tools/release_reports.sh

What it produces:
  out/exports/<timestamp>.zip
  and copies latest zip to:
  ~/storage/downloads/

Zip must include:
  standings__normalized.csv
  goal_timing__normalized.csv
  passes_players_split__normalized.csv
  goal_timing_team_profile.csv
  passes_players_top_attempted.csv
  passes_players_top_pct_min50.csv
  passes_team_summary.csv
  manifest.json
  (optional) passes_aggregate__normalized.csv
  (optional) passes_clean__normalized.csv
  (optional) tables_catalog.txt

Manifest:
  out/summaries/manifest.json
