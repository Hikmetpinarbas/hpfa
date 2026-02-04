import csv
from engine.map.canonical_mapper import load_mapping, map_columns, capability_report

def inspect_csv(path, mapping_path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)

    mapping = load_mapping(mapping_path)
    col_map, missing = map_columns(headers, mapping)
    report = capability_report(headers, mapping)

    return {
        "headers": headers,
        "column_map": col_map,
        "capability": report
    }