from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Optional

def load_json(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))

def load_ontology(root: str | Path) -> dict:
    root = Path(root)
    return load_json(root / "metric_ontology.json")

def load_platform_mappings(root: str | Path) -> dict:
    root = Path(root)
    return load_json(root / "platform_mappings.json")
