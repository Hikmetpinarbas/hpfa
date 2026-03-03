from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

class RawCellType(str, Enum):
    UNKNOWN = "unknown"
    STRING = "string"
    NUMBER = "number"
    BOOL = "bool"
    DATE = "date"
    DATETIME = "datetime"

@dataclass
class RawColumn:
    name: str
    source_name: Optional[str] = None
    inferred_type: RawCellType = RawCellType.UNKNOWN
    notes: List[str] = field(default_factory=list)

@dataclass
class RawTable:
    format: str
    source: str
    table_name: str
    columns: List[RawColumn]
    rows: List[Dict[str, Any]]
    warnings: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)
