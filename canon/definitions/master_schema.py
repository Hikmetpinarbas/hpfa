from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    dtype: str
    nullable: bool
    group: str


@dataclass(frozen=True)
class EnumSpec:
    name: str
    canonical: List[str]
    fallback: str
    max_new_values_per_pr: int


@dataclass(frozen=True)
class SchemaSpec:
    schema_name: str
    schema_version: str
    released_at: str
    groups: Dict[str, Dict[str, Any]]
    enums: Dict[str, EnumSpec]
    constraints: Dict[str, Any]

    def flat_columns(self) -> Dict[str, ColumnSpec]:
        cols: Dict[str, ColumnSpec] = {}
        for group_name, group_meta in self.groups.items():
            colmap = group_meta.get("columns", {})
            for col_name, spec in colmap.items():
                cols[col_name] = ColumnSpec(
                    name=col_name,
                    dtype=str(spec["dtype"]),
                    nullable=bool(spec["nullable"]),
                    group=group_name,
                )
        return cols

    def required_groups(self) -> List[str]:
        out: List[str] = []
        for group_name, group_meta in self.groups.items():
            if bool(group_meta.get("required", False)):
                out.append(group_name)
        return out

    def required_columns(self) -> List[str]:
        cols: List[str] = []
        for group_name in self.required_groups():
            colmap = self.groups[group_name].get("columns", {})
            cols.extend(list(colmap.keys()))
        return cols


def load_schema(path: str | Path) -> SchemaSpec:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))

    enums: Dict[str, EnumSpec] = {}
    for enum_name, enum_meta in data.get("enums", {}).items():
        enums[enum_name] = EnumSpec(
            name=enum_name,
            canonical=[str(x) for x in enum_meta.get("canonical", [])],
            fallback=str(enum_meta.get("fallback", "")),
            max_new_values_per_pr=int(enum_meta.get("max_new_values_per_pr", 0)),
        )

    return SchemaSpec(
        schema_name=str(data["schema_name"]),
        schema_version=str(data["schema_version"]),
        released_at=str(data.get("released_at", "")),
        groups=dict(data["groups"]),
        enums=enums,
        constraints=dict(data.get("constraints", {})),
    )


def default_schema_path() -> Path:
    # repo_root/canon/definitions/master_schema.py -> repo_root/canon/schemas/...
    here = Path(__file__).resolve()
    repo_root = here.parents[2]
    return repo_root / "canon" / "schemas" / "hpcdl_v1.0.0.json"
