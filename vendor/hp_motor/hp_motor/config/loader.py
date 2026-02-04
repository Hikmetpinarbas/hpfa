from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict

def load_spec(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)
