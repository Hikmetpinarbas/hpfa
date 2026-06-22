#!/usr/bin/env python3
from __future__ import annotations
import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


def read_events(path: str) -> List[Dict[str, Any]]:
    p = Path(path)
    if p.suffix.lower() == '.jsonl':
        rows = []
        with p.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows
    if p.suffix.lower() == '.json':
        data = json.loads(p.read_text(encoding='utf-8'))
        if isinstance(data, dict) and isinstance(data.get('events'), list):
            return list(data['events'])
        if isinstance(data, list):
            return list(data)
        raise ValueError('json input must be events[] or list')
    with p.open('r', encoding='utf-8-sig', newline='') as f:
        sample = f.read(4096)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=',;\t') if sample else csv.excel
        return list(csv.DictReader(f, dialect=dialect))


def write_jsonl(path: str, rows: Iterable[Dict[str, Any]]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')


def write_json(path: str, payload: Dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding='utf-8')
