#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path
from datetime import datetime

REG_PATH = Path("hp_motor/library/registry/metric_registry.json")

MANUAL_DEFS_TR = {
    "M_PASS_COUNT": "Toplam pas sayısı. (Seçilen segment/sekans/faz içinde atılan pasların adedi.)",
    "M_PROG_PASS_COUNT": "Progressive (ilerletici) pas sayısı. Topu rakip kaleye doğru anlamlı ölçüde taşıyan pasların adedi. Eşik/hesap yöntemi proje standardına göre tanımlıdır.",
    "M_SHOT_COUNT": "Toplam şut sayısı. (Seçilen segment/sekans/faz içinde çekilen şutların adedi.)",
    "M_TURNOVER_COUNT": "Top kaybı (turnover) sayısı. Topa sahipken topun rakibe geçtiği kayıpların adedi (pas hatası, dripling kaybı, kontrol hatası vb. dahil).",
    "M_SEQUENCE_LENGTH": "Sekans uzunluğu. Bir sekansın içindeki olay/aksiyon sayısı (event-count). Sekans tanımı segmentation modülünün kural setine göre yapılır.",
}

MISSING_SOURCE_IDS = [
    "SB_BALL_RECOVERIES_AFTER_LOSSES_WITHIN_5_SECONDS",
    "SB_CHANCES_SUCCESSFUL",
    "SB_FINAL_THIRD_ENTRIES",
    "SB_KEY_PASSES_ACCURATE",
    "SB_KILIT_PAS",
    "SB_KONTRA_ATAKLAR",
    "SB_PPDA",
    "SB_PROGRESSIVE_OPEN_PASSES",
    "SB_PROGRESSIVE_PASSES",
    "SB_RAKIP_SAHADA_GERI_KAZANILAN_TOPLAR",
    "SB_SUT_BASINA_XG",
    "SB_SUTLA_BITEN_KONTRA_ATAKLAR",
]

def backup_file(p: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    b = p.with_suffix(f".bak_{ts}.json")
    b.write_bytes(p.read_bytes())
    return b

def main():
    if not REG_PATH.exists():
        raise SystemExit(f"Registry not found: {REG_PATH}")

    backup = backup_file(REG_PATH)

    reg = json.load(REG_PATH.open("r", encoding="utf-8"))
    metrics = reg.get("metrics", [])
    by_id = {m.get("id"): m for m in metrics if isinstance(m, dict) and m.get("id")}

    # 1) Fill missing 5 with manual definitions (only if truly missing)
    filled_manual = 0
    for mid, dtr in MANUAL_DEFS_TR.items():
        m = by_id.get(mid)
        if not m:
            continue
        if (m.get("definition_tr") or "").strip() or (m.get("definition_en") or "").strip():
            continue
        m["definition_tr"] = dtr
        m["definition_source"] = "manual_hp"
        m["definition_confidence"] = 0.95
        filled_manual += 1

    # 2) Add source for SB_* metrics where definition exists but source missing
    fixed_sources = 0
    for mid in MISSING_SOURCE_IDS:
        m = by_id.get(mid)
        if not m:
            continue
        has_def = bool((m.get("definition_tr") or "").strip() or (m.get("definition_en") or "").strip())
        has_src = bool((m.get("definition_source") or "").strip())
        if has_def and not has_src:
            m["definition_source"] = "sportsbase_vendor"
            # confidence: keep existing if present, else set
            if m.get("definition_confidence") is None:
                m["definition_confidence"] = 0.85
            fixed_sources += 1

    json.dump(reg, REG_PATH.open("w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("OK: registry fixed")
    print("backup:", str(backup))
    print("filled_manual:", filled_manual)
    print("fixed_sources:", fixed_sources)

if __name__ == "__main__":
    main()
