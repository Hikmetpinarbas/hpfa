import yaml
from collections import defaultdict

def load_mapping(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def map_columns(headers, mapping):
    col_map = {}
    missing_required = []

    for col, spec in mapping["columns"].items():
        found = None
        for a in spec.get("aliases", []):
            if a in headers:
                found = a
                break
        if found:
            col_map[found] = spec["target"]
        elif spec.get("required"):
            missing_required.append(col)

    return col_map, missing_required

def capability_report(headers, mapping):
    _, missing = map_columns(headers, mapping)
    return {
        "status": "BLOCKED" if missing else "OK",
        "missing_required": missing
    }