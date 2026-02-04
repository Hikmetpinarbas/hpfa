from __future__ import annotations

import json
from pathlib import Path
from typing import List


def _repo_root() -> Path:
    # engine/metrics/api.py -> engine/metrics -> engine -> repo root
    return Path(__file__).resolve().parents[2]


def list_metric_ids(debug: bool = False) -> List[str]:
    """
    CI-safe metric listing.
    - Asla exception fırlatmaz
    - Registry varsa okur
    - Yoksa canon/metrics altını tarar
    """

    root = _repo_root()
    found = []

    # 1) Registry dene
    registry = root / "canon" / "metrics" / "registry.json"
    if registry.exists():
        try:
            data = json.loads(registry.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "metrics" in data:
                found = [m["metric_id"] for m in data["metrics"] if "metric_id" in m]
                if debug:
                    print("SOURCE=registry.json", found[:10])
                return found
        except Exception as e:
            if debug:
                print("REGISTRY ERROR:", e)

    # 2) Spec taraması
    spec_root = root / "canon" / "metrics"
    if not spec_root.exists():
        if debug:
            print("NO canon/metrics DIRECTORY")
        return []

    for p in spec_root.rglob("*.json"):
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(doc, dict) and "metric_id" in doc:
                found.append(doc["metric_id"])
        except Exception as e:
            if debug:
                print("BAD JSON:", p.as_posix(), e)

    if debug:
        print("SOURCE=scan", found[:10])

    # uniq
    return list(dict.fromkeys(found))


def get_metric(metric_id: str):
    return None


def search_metrics(query: str):
    return []