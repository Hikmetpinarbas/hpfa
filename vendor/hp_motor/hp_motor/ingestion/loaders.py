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
