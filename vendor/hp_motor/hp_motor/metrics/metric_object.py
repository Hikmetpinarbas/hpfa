from dataclasses import dataclass
from typing import Any

@dataclass
class MetricObject:
    name: str
    value: Any
    status: str          # OK / WEAK / PROXY / UNKNOWN
    evidence: str
    interpretation: str

    def as_dict(self) -> dict:
        return {
            "metric": self.name,
            "value": self.value,
            "status": self.status,
            "evidence": self.evidence,
            "interpretation": self.interpretation,
        }
