from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, asdict
from typing import Any

ALLOWED_SOURCES = {"TERMUX", "GITHUB", "GOOGLE_DRIVE", "DROPBOX", "SIDER_SCHOLAR"}
CLAIM_SAFETY = "REFERENCE_ONLY_UNTIL_ACTIVE_MATCH_VALIDATION"


def normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_") or "unknown"


@dataclass(frozen=True)
class SourceIntake:
    source_system: str
    title: str
    source_path: str
    capability_family: str
    hpfa_capability: str
    claim_safety: str = CLAIM_SAFETY

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_intake(raw: dict[str, Any]) -> SourceIntake:
    source_system = str(raw.get("source_system", "")).upper().strip()
    if source_system not in ALLOWED_SOURCES:
        raise ValueError(f"unsupported source_system: {source_system}")

    return SourceIntake(
        source_system=source_system,
        title=str(raw.get("title", "unknown")).strip() or "unknown",
        source_path=str(raw.get("source_path", "unknown")).strip() or "unknown",
        capability_family=normalize_text(raw.get("capability_family", "unknown")),
        hpfa_capability=normalize_text(raw.get("hpfa_capability", "unknown")),
        claim_safety=str(raw.get("claim_safety", CLAIM_SAFETY)).strip() or CLAIM_SAFETY,
    )


def discovery_fingerprint(intake: SourceIntake) -> str:
    base = f"{normalize_text(intake.title)}|{intake.capability_family}|{intake.hpfa_capability}"
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]
    return f"HASH:{digest}"
