import os, json
from pathlib import Path

out_dir = os.environ.get("OUT_DIR")
if not out_dir:
    raise SystemExit("[FAIL] OUT_DIR not set")

out = Path(out_dir)
need = [
    "engine_meta_stamped.json",
    "engine_seq_possessions.json",
    "engine_xt01_grid.json",
    "engine_gate_report.json",
]
for f in need:
    p = out / f
    if not p.exists():
        raise SystemExit(f"[FAIL] missing: {p}")

payload = {
    "out_dir": out.as_posix(),
    "engine_meta_stamped": json.loads((out/"engine_meta_stamped.json").read_text(encoding="utf-8")),
    "engine_gate_report": json.loads((out/"engine_gate_report.json").read_text(encoding="utf-8")),
    "artifacts": {
        "engine_seq_possessions": str(out/"engine_seq_possessions.json"),
        "engine_xt01_grid": str(out/"engine_xt01_grid.json"),
    },
}

dst = out / "motor_payload.json"
dst.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
print("[OK] wrote:", dst)
print("[OK] gate_action:", payload["engine_gate_report"].get("action"))
