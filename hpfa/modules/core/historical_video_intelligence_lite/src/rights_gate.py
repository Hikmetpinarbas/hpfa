"""Source and rights admission gate for video inputs.

The gate never decides legality. It checks that an operator has recorded a
rights basis, that acquisition did not involve circumventing a download or
access protection, and it keeps processing permission separate from
publication permission. Unknown rights FAIL_CLOSED.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROCESSING_ALLOWED_STATUSES = {
    "OPEN_LICENSE",
    "LICENSED",
    "OPERATOR_ATTESTED_LAWFUL_ACCESS",
}
KNOWN_STATUSES = PROCESSING_ALLOWED_STATUSES | {
    "UNKNOWN",
    "REVIEW_REQUIRED",
    "NOT_CLEARED",
}
FORBIDDEN_ACQUISITION = {
    "DRM_CIRCUMVENTION",
    "DOWNLOAD_PROTECTION_BYPASS",
    "STREAM_RIPPING_WITHOUT_PERMISSION",
    "ACCOUNT_OR_GEO_RESTRICTION_BYPASS",
    "UNKNOWN",
}
REQUIRED_FIELDS = (
    "manifest_id",
    "video_id",
    "rights_status",
    "acquisition_method",
    "download_protection_circumvented",
    "publication_cleared",
)


def load_manifest(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evaluate_rights(manifest: dict[str, Any] | None) -> dict[str, Any]:
    blocks: list[str] = []
    review: list[str] = []
    if not manifest:
        return {
            "status": "FAIL_CLOSED",
            "processing_allowed": False,
            "publication_allowed": False,
            "hard_block_hits": ["rights_manifest_missing"],
            "review_hits": [],
        }
    for field in REQUIRED_FIELDS:
        if field not in manifest:
            blocks.append(f"rights_manifest_missing_field:{field}")
    status = manifest.get("rights_status")
    if status not in KNOWN_STATUSES:
        blocks.append("rights_status_unrecognised")
    elif status not in PROCESSING_ALLOWED_STATUSES:
        blocks.append(f"rights_status_not_cleared:{status}")
    if manifest.get("download_protection_circumvented") is not False:
        blocks.append("download_protection_circumvention_not_excluded")
    if manifest.get("acquisition_method") in FORBIDDEN_ACQUISITION:
        blocks.append(f"acquisition_method_not_admissible:{manifest.get('acquisition_method')}")
    if status == "OPEN_LICENSE":
        if not manifest.get("license") or not manifest.get("license_url"):
            blocks.append("open_license_without_license_reference")
        if not manifest.get("attribution"):
            review.append("attribution_text_missing")
    if status == "OPERATOR_ATTESTED_LAWFUL_ACCESS" and not manifest.get("attestation"):
        blocks.append("operator_attestation_text_missing")

    processing_allowed = not blocks
    publication_allowed = processing_allowed and manifest.get("publication_cleared") is True
    return {
        "status": "PASS" if processing_allowed and not review else ("REVIEW_REQUIRED" if processing_allowed else "FAIL_CLOSED"),
        "manifest_id": manifest.get("manifest_id"),
        "rights_status": status,
        "processing_allowed": processing_allowed,
        "publication_allowed": publication_allowed,
        "publication_scope": "DERIVED_EVENT_DATA_AND_MEDIA" if publication_allowed else "NONE",
        "hard_block_hits": blocks,
        "review_hits": review,
        "legal_determination_made": False,
    }


def require_processing(manifest: dict[str, Any] | None) -> dict[str, Any]:
    verdict = evaluate_rights(manifest)
    if not verdict["processing_allowed"]:
        raise PermissionError("rights_gate_fail_closed:" + ",".join(verdict["hard_block_hits"]))
    return verdict
