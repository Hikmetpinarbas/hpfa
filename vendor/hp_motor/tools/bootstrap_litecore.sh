#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# Must run from repo root
if [ ! -d ".git" ]; then
  echo "ERROR: Repo root degilsin. .git bulunamadi. 'cd ~/hp_motor' ile gel."
  exit 1
fi

echo "[1/6] Creating directories..."
mkdir -p hp_motor/config hp_motor/ontology
mkdir -p hp_motor/library/registry hp_motor/library/patterns
mkdir -p hp_motor/ingestion hp_motor/segmentation hp_motor/metrics
mkdir -p hp_motor/context/rules hp_motor/report
mkdir -p tests/fixtures tools

echo "[2/6] Writing requirements.txt ..."
cat > requirements.txt << 'REQ'
PyYAML>=6.0.0,<7.0.0
pytest>=7.0.0,<9.0.0
REQ

echo "[3/6] Writing core package files..."
cat > hp_motor/__init__.py << 'PY'
__all__ = ["__version__"]
__version__ = "0.1.0-litecore"
PY

cat > hp_motor/config/spec.json << 'JSON'
{
  "hp_motor": {
    "version": "0.1.0-litecore",
    "ontology_version": "0.1.0",
    "progressive_pass_dx_threshold": 15.0
  }
}
JSON

cat > hp_motor/config_reader.py << 'PY'
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict

_SPEC_CACHE: Dict[str, Any] | None = None

def read_spec() -> Dict[str, Any]:
    global _SPEC_CACHE
    if _SPEC_CACHE is not None:
        return _SPEC_CACHE
    p = Path(__file__).resolve().parent / "config" / "spec.json"
    if not p.exists():
        _SPEC_CACHE = {"hp_motor": {"version": "missing", "ontology_version": "missing"}}
        return _SPEC_CACHE
    with p.open("r", encoding="utf-8") as f:
        _SPEC_CACHE = json.load(f)
        return _SPEC_CACHE
PY

cat > hp_motor/library/loader.py << 'PY'
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

SDCARD_ROOT = Path("/sdcard/HP_LIBRARY")

@dataclass(frozen=True)
class LibraryHealth:
    status: str
    flags: List[str]
    roots_checked: List[str]

def _project_root() -> Path:
    return Path(__file__).resolve().parent

def _roots() -> List[Path]:
    return [_project_root(), SDCARD_ROOT]

def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def _resolve(rel: str) -> Tuple[Path | None, LibraryHealth]:
    flags: List[str] = []
    checked: List[str] = []
    for r in _roots():
        checked.append(str(r))
        p = r / rel
        if p.exists() and p.is_file():
            return p, LibraryHealth(status="OK", flags=[], roots_checked=checked)
    flags.append(f"missing_artifact:{rel}")
    return None, LibraryHealth(status="DEGRADED", flags=flags, roots_checked=checked)

def load_registry() -> Tuple[Dict[str, Any], LibraryHealth]:
    p, h = _resolve("registry/metric_registry.json")
    if not p:
        return {"metrics": [], "version": "missing"}, h
    return _read_json(p), h

def load_vendor_mappings() -> Tuple[Dict[str, Any], LibraryHealth]:
    p, h = _resolve("registry/vendor_mappings.json")
    if not p:
        return {"vendor": {}, "version": "missing"}, h
    return _read_json(p), h
PY

cat > hp_motor/library/registry/metric_registry.json << 'JSON'
{
  "version": "0.1.0",
  "metrics": [
    {"id":"M_PASS_COUNT","label":"Pass Count","layer":"micro","mechanisms":["kontrol","ilerletme"],"definition":"Number of pass events.","status_policy":"OK|DEGRADED|UNKNOWN"},
    {"id":"M_PROG_PASS_COUNT","label":"Progressive Pass Count","layer":"micro","mechanisms":["ilerletme","risk"],"definition":"Passes with (end_x-start_x) >= threshold.","status_policy":"OK|DEGRADED|UNKNOWN"},
    {"id":"M_SHOT_COUNT","label":"Shot Count","layer":"micro","mechanisms":["deger","risk"],"definition":"Number of shot events.","status_policy":"OK|DEGRADED|UNKNOWN"},
    {"id":"M_TURNOVER_COUNT","label":"Turnover Count","layer":"micro","mechanisms":["risk"],"definition":"Vendor-neutral proxy of possession-losing events.","status_policy":"OK|DEGRADED|UNKNOWN"}
  ]
}
JSON

cat > hp_motor/library/registry/vendor_mappings.json << 'JSON'
{
  "version": "0.1.0",
  "vendor": {
    "generic": {
      "event_type": "event_type",
      "team_id": "team_id",
      "match_id": "match_id",
      "period": "period",
      "minute": "minute",
      "second": "second",
      "player_id": "player_id",
      "possession_id": "possession_id",
      "sequence_id": "sequence_id",
      "start_x": "start_x",
      "start_y": "start_y",
      "end_x": "end_x",
      "end_y": "end_y",
      "outcome": "outcome",
      "sot": "sot",
      "set_piece_state": "set_piece_state",
      "phase": "phase"
    }
  }
}
JSON

cat > hp_motor/ingestion/loaders.py << 'PY'
from __future__ import annotations
import csv, json
from pathlib import Path
from typing import Any, Dict, List

def load_events(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    s = path.suffix.lower()
    if s == ".json":
        with path.open("r", encoding="utf-8") as f:
            obj = json.load(f)
            if isinstance(obj, list): return obj
            if isinstance(obj, dict) and isinstance(obj.get("events"), list): return obj["events"]
            return []
    if s == ".jsonl":
        out: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line=line.strip()
                if line: out.append(json.loads(line))
        return out
    if s == ".csv":
        with path.open("r", encoding="utf-8") as f:
            return [dict(r) for r in csv.DictReader(f)]
    return []
PY

cat > hp_motor/ingestion/normalizers.py << 'PY'
from __future__ import annotations
from typing import Any, Dict, List
from hp_motor.library.loader import load_vendor_mappings

def _to_int(v: Any, d: int = 0) -> int:
    try: return int(float(v))
    except Exception: return d

def _to_float(v: Any, d: float = 0.0) -> float:
    try: return float(v)
    except Exception: return d

def normalize_events(events: List[Dict[str, Any]], vendor: str = "generic") -> List[Dict[str, Any]]:
    mappings, _ = load_vendor_mappings()
    vmap = mappings.get("vendor", {}).get(vendor) or mappings.get("vendor", {}).get("generic", {})
    out: List[Dict[str, Any]] = []
    for e in events:
        ne: Dict[str, Any] = {}
        for ck, vk in vmap.items():
            if vk in e: ne[ck] = e[vk]
        for k in ["match_id","team_id","period","minute","second","event_type","player_id",
                  "possession_id","sequence_id","start_x","start_y","end_x","end_y","outcome","sot","set_piece_state","phase"]:
            if k in e and k not in ne: ne[k] = e[k]

        ne["period"] = _to_int(ne.get("period", 1), 1)
        ne["minute"] = _to_int(ne.get("minute", 0), 0)
        ne["second"] = _to_int(ne.get("second", 0), 0)
        for fk in ["start_x","start_y","end_x","end_y"]:
            if fk in ne: ne[fk] = _to_float(ne[fk], 0.0)
        ne["event_type"] = str(ne.get("event_type","")).strip().lower()
        if "outcome" in ne: ne["outcome"] = str(ne["outcome"]).strip().lower()
        out.append(ne)
    return out
PY

cat > hp_motor/segmentation/set_piece_state.py << 'PY'
from __future__ import annotations
from typing import Any, Dict, List

SET_PIECE_KEYWORDS = {"corner":"corner","free_kick":"free_kick","throw_in":"throw_in","penalty":"penalty","kick_off":"kick_off"}

def tag_set_piece_state(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for e in events:
        if e.get("set_piece_state"):
            e["set_piece_state"] = str(e["set_piece_state"]).strip().lower()
            continue
        et = str(e.get("event_type","")).lower()
        sp = "open_play"
        for k,v in SET_PIECE_KEYWORDS.items():
            if k in et:
                sp = v
                break
        e["set_piece_state"] = sp
    return events
PY

cat > hp_motor/segmentation/phase_tagger.py << 'PY'
from __future__ import annotations
from typing import Any, Dict, List

def tag_phases(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for e in events:
        if e.get("phase"):
            e["phase"] = str(e["phase"]).strip().upper()
            continue
        et = str(e.get("event_type","")).lower()
        if any(k in et for k in ["recovery","interception","counter","transition"]):
            ph = "P6_TRANSITION"
        elif any(k in et for k in ["press","pressure"]):
            ph = "P5_DEF_PRESS"
        elif any(k in et for k in ["block","clearance"]):
            ph = "P4_DEF_BLOCK"
        elif any(k in et for k in ["shot","cross","key_pass","chance"]):
            ph = "P3_ATTACK_FINAL"
        elif any(k in et for k in ["carry","dribble","progressive","through"]):
            ph = "P2_ATTACK_PROG"
        else:
            ph = "P1_ATTACK_BUILD"
        e["phase"] = ph
    return events
PY

cat > hp_motor/metrics/factory.py << 'PY'
from __future__ import annotations
from typing import Any, Dict, List
from hp_motor.config_reader import read_spec

def compute_raw_metrics(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    spec = read_spec()
    prog_dx = float(spec.get("hp_motor", {}).get("progressive_pass_dx_threshold", 15.0))

    pass_count = 0
    prog_pass = 0
    shot = 0
    turnover = 0
    have_xy = True

    for e in events:
        et = str(e.get("event_type","")).lower()

        if et == "pass":
            pass_count += 1
            if "start_x" in e and "end_x" in e:
                try:
                    dx = float(e["end_x"]) - float(e["start_x"])
                    if dx >= prog_dx: prog_pass += 1
                except Exception:
                    have_xy = False
            else:
                have_xy = False

        if "shot" in et:
            shot += 1

        if et in {"turnover","dispossessed"}:
            turnover += 1
        if et == "pass" and str(e.get("outcome","")).lower() in {"fail","failed","incomplete","lost"}:
            turnover += 1
        if et in {"carry","dribble"} and str(e.get("outcome","")).lower() in {"fail","failed","lost"}:
            turnover += 1

    return {
        "meta": {"thresholds": {"progressive_pass_dx": prog_dx}, "counts": {"events": len(events)}},
        "metrics": {
            "M_PASS_COUNT": {"value": pass_count, "status": "OK"},
            "M_PROG_PASS_COUNT": {"value": prog_pass, "status": "OK" if have_xy else "DEGRADED"},
            "M_SHOT_COUNT": {"value": shot, "status": "OK"},
            "M_TURNOVER_COUNT": {"value": turnover, "status": "OK" if turnover > 0 else "DEGRADED"}
        }
    }
PY

cat > hp_motor/context/engine.py << 'PY'
from __future__ import annotations
from typing import Any, Dict, List, Tuple

def apply_context(metrics_raw: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    # Lite: identity adjustment + flags
    flags = ["context:identity_v0"]
    adj = {"meta": dict(metrics_raw.get("meta", {})), "metrics": {}}
    for mid, p in metrics_raw.get("metrics", {}).items():
        adj["metrics"][mid] = {
            "value": p.get("value"),
            "status": p.get("status"),
            "adjustment": {"method": "identity_v0", "note": "Lite Core: adjustments deferred; flags provided."}
        }
    return adj, flags
PY

cat > hp_motor/report/schema.py << 'PY'
from __future__ import annotations
from typing import Any, Dict

REQUIRED_TOP_KEYS = ["hp_motor_version","ontology_version","popper","events_summary","metrics_raw","metrics_adjusted","context_flags","output_standard"]

def validate_report(report: Dict[str, Any]) -> None:
    missing = [k for k in REQUIRED_TOP_KEYS if k not in report]
    if missing:
        raise ValueError(f"Report schema missing keys: {missing}")
    if "status" not in report.get("popper", {}):
        raise ValueError("Report schema: popper.status missing")
PY

cat > hp_motor/report/generator.py << 'PY'
from __future__ import annotations
from typing import Any, Dict, List
from hp_motor import __version__
from hp_motor.config_reader import read_spec

def generate_report(popper_status: str, hard_errors: List[str], flags: List[str], events_summary: Dict[str, Any],
                    metrics_raw: Dict[str, Any], metrics_adjusted: Dict[str, Any], context_flags: List[str]) -> Dict[str, Any]:
    spec = read_spec()
    ontology_version = spec.get("hp_motor", {}).get("ontology_version", "0.1.0")
    return {
        "hp_motor_version": __version__,
        "ontology_version": ontology_version,
        "popper": {"status": popper_status, "hard_errors": hard_errors, "flags": flags},
        "events_summary": events_summary,
        "metrics_raw": metrics_raw,
        "metrics_adjusted": metrics_adjusted,
        "context_flags": context_flags,
        "output_standard": {"findings": [], "reasons": [], "evidence": [], "actions": [], "risks_assumptions": []}
    }
PY

cat > hp_motor/pipeline.py << 'PY'
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List

from hp_motor.ingestion.loaders import load_events
from hp_motor.ingestion.normalizers import normalize_events
from hp_motor.segmentation.set_piece_state import tag_set_piece_state
from hp_motor.segmentation.phase_tagger import tag_phases
from hp_motor.metrics.factory import compute_raw_metrics
from hp_motor.context.engine import apply_context
from hp_motor.report.generator import generate_report
from hp_motor.report.schema import validate_report

REQUIRED = ["match_id","team_id","period","minute","second","event_type"]

def _popper(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not events:
        return {"status":"BLOCKED","hard_errors":["events_table_missing_or_empty"],"flags":[]}
    # SOT hard block
    for e in events[:50]:
        sot = str(e.get("sot","")).upper().strip()
        if sot in {"ERROR","BROKEN"}:
            return {"status":"BLOCKED","hard_errors":[f"sot_hard_block:{sot}"],"flags":[]}
    missing = [c for c in REQUIRED if all(c not in e for e in events)]
    if missing:
        return {"status":"BLOCKED","hard_errors":[f"missing_required_columns:{missing}"],"flags":[]}
    return {"status":"OK","hard_errors":[],"flags":[]}

def run_pipeline(events_path: Path, vendor: str = "generic") -> Dict[str, Any]:
    raw = load_events(events_path)
    pop = _popper(raw)
    if pop["status"] == "BLOCKED":
        rep = generate_report(popper_status="BLOCKED", hard_errors=pop["hard_errors"], flags=[],
                              events_summary={"n_events": len(raw) if raw else 0},
                              metrics_raw={}, metrics_adjusted={}, context_flags=[])
        validate_report(rep)
        return rep

    events = normalize_events(raw, vendor=vendor)
    events = tag_set_piece_state(events)
    events = tag_phases(events)

    metrics_raw = compute_raw_metrics(events)
    metrics_adj, ctx_flags = apply_context(metrics_raw)

    rep = generate_report(popper_status="OK", hard_errors=[], flags=[],
                          events_summary={"n_events": len(events)},
                          metrics_raw=metrics_raw, metrics_adjusted=metrics_adj, context_flags=ctx_flags)
    validate_report(rep)
    return rep
PY

cat > hp_motor/cli.py << 'PY'
import argparse, json
from pathlib import Path
from hp_motor.pipeline import run_pipeline

def main() -> int:
    p = argparse.ArgumentParser(prog="hp_motor", description="HP Motor Lite Core CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="Run lite-core pipeline and output report json")
    r.add_argument("--events", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--vendor", default="generic")

    a = p.parse_args()
    if a.cmd == "run":
        rep = run_pipeline(Path(a.events), vendor=a.vendor)
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"OK: wrote {out}")
        return 0
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
PY

echo "[4/6] Writing test fixture..."
cat > tests/fixtures/events_min.json << 'JSON'
[
  {"match_id":"m1","team_id":"A","period":1,"minute":0,"second":5,"event_type":"pass","player_id":"p1","start_x":20,"start_y":40,"end_x":28,"end_y":41,"outcome":"complete","possession_id":"pos1"},
  {"match_id":"m1","team_id":"A","period":1,"minute":0,"second":10,"event_type":"pass","player_id":"p2","start_x":28,"start_y":41,"end_x":47,"end_y":44,"outcome":"complete","possession_id":"pos1"},
  {"match_id":"m1","team_id":"A","period":1,"minute":0,"second":18,"event_type":"shot","player_id":"p9","start_x":88,"start_y":40,"end_x":100,"end_y":40,"outcome":"on_target","possession_id":"pos1"},
  {"match_id":"m1","team_id":"B","period":1,"minute":1,"second":2,"event_type":"pass","player_id":"q4","start_x":30,"start_y":55,"end_x":38,"end_y":57,"outcome":"failed","possession_id":"pos2"},
  {"match_id":"m1","team_id":"A","period":1,"minute":1,"second":10,"event_type":"recovery","player_id":"p6","possession_id":"pos3"}
]
JSON

echo "[5/6] Installing deps..."
python -m pip install -U pip >/dev/null
pip install -r requirements.txt >/dev/null

echo "[6/6] Done. Next: export PYTHONPATH and run CLI."
