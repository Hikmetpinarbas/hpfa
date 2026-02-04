import json
from pathlib import Path

_REGISTRY_PATH = Path(__file__).parent / "registry.json"

def load_registry():
    if not _REGISTRY_PATH.exists():
        raise FileNotFoundError(
            f"Metric registry not found at {_REGISTRY_PATH}. "
            "Did you run build_registry?"
        )
    with open(_REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_metric_spec(metric_id: str):
    reg = load_registry()
    metrics = reg.get("metrics", {})
    if metric_id not in metrics:
        raise KeyError(f"Metric '{metric_id}' not found in registry")
    return metrics[metric_id] 