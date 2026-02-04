# engine/hp_engine_core.py
import os, json
from datetime import datetime
from hp_engine_reader import universal_reader, normalize_to_json

def run_analysis(file_path):
    print(f"🔍 Processing: {file_path}")
    
    try:
        data = universal_reader(file_path)
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return None

    # JSON’a dönüştürme (loglama için)
    json_path = f"output/reports/{os.path.basename(file_path)}.json"
    normalize_to_json(data, json_path)

    # Örnek basit metrik hesapları
    results = {
        "source_file": os.path.basename(file_path),
        "total_items": len(data) if isinstance(data, list) else 1,
        "format": os.path.splitext(file_path)[-1],
        "xG_estimate": 1.37,
        "ppda_estimate": 8.3,
        "transition_efficiency": 0.76,
        "saved_json": json_path,
        "timestamp": datetime.now().isoformat()
    }

    report_file = f"output/reports/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs("output/reports", exist_ok=True)
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    print(f"✅ Analysis complete: {report_file}")
    return results