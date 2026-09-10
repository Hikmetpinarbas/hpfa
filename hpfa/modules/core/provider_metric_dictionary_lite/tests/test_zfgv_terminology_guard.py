from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
MIGRATION_LEDGER = ROOT / "docs" / "governance" / "zfgv_event_only_migration_inventory_v1.md"
OBSERVATION_CONTRACT = (
    ROOT
    / "hpfa"
    / "modules"
    / "core"
    / "observation_contract_lite"
    / "src"
    / "observation_contract.py"
)
LEGACY_PROVIDER_IMPL = (
    ROOT
    / "hpfa"
    / "modules"
    / "core"
    / "provider_metric_dictionary_lite"
    / "src"
    / "_provider_metric_dictionary_impl_v7.py"
)


class ZFGVTerminologyGuardTests(unittest.TestCase):
    def test_migration_ledger_explicitly_allows_classified_legacy_terminology(self):
        text = MIGRATION_LEDGER.read_text(encoding="utf-8")
        self.assertIn(
            "The test is not whether the phrase `event-only` appears.",
            text,
        )
        for classification in (
            "PRESERVE_AS_GUARD",
            "GENERALIZE",
            "RENAME",
            "SUPERSEDE",
            "REVIEW_REQUIRED",
        ):
            self.assertIn(classification, text)

    def test_zfgv_is_the_authoritative_observation_contract(self):
        text = OBSERVATION_CONTRACT.read_text(encoding="utf-8")
        self.assertIn('OBSERVATION_MODEL = "ZFGV_V1"', text)
        self.assertIn('"event_only_is_product_ceiling": False', text)
        self.assertIn("Deprecated compatibility metadata only", text)

    def test_historical_provider_engine_no_longer_uses_event_only_as_runtime_gate(self):
        text = LEGACY_PROVIDER_IMPL.read_text(encoding="utf-8")
        gate_patterns = (
            r"event_only_compatible\s*\)\s+is\s+(?:True|False)",
            r"event_only_compatible\s*==\s*(?:True|False)",
            r"if\s+[^\n]*event_only_compatible",
            r"event_only_compatibility_required",
        )
        hits = [pattern for pattern in gate_patterns if re.search(pattern, text)]
        self.assertEqual(
            hits,
            [],
            "legacy provider implementation must not use event-only compatibility as a product gate",
        )


if __name__ == "__main__":
    unittest.main()
