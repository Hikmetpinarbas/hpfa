#!/data/data/com.termux/files/usr/bin/sh
set -e
echo "[HP-Motor] Step12..."
python STEP12_PHASE_TAGGER_MVP.py --match-pack MATCH_PACK
echo "[HP-Motor] Step13..."
python STEP13_TEMPO_MOMENTS.py --match-pack MATCH_PACK
echo "[HP-Motor] Step14..."
python STEP14_BRIEF_V2_RENDER.py --match-pack MATCH_PACK
echo "DONE. Outputs in MATCH_PACK/out/"
