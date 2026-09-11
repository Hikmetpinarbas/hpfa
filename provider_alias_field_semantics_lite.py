from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "provider_alias_field_semantics_lite" / "src"
sys.path.insert(0, str(SRC))

import provider_alias_field_semantics as core
from provider_semantic_mapping_provenance import enrich_mapping_provenance

_original_build_semantics = core.build_semantics


def _build_semantics_with_mapping_provenance(csv_payload, xlsx_payload, xml_payload):
    result = _original_build_semantics(csv_payload, xlsx_payload, xml_payload)
    return enrich_mapping_provenance(
        result,
        csv_payload=csv_payload,
        xlsx_payload=xlsx_payload,
        xml_payload=xml_payload,
    )


core.build_semantics = _build_semantics_with_mapping_provenance
main = core.main

if __name__ == "__main__":
    raise SystemExit(main())
