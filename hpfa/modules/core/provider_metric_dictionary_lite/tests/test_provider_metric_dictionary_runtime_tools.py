from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BOOTSTRAP = ROOT / "tools" / "bootstrap_termux_provider_metric_dictionary_v1.sh"
RUNNER = ROOT / "tools" / "run_active_match_provider_metric_dictionary_v1.sh"


class ProviderMetricDictionaryRuntimeToolTests(unittest.TestCase):
    def test_runtime_tools_are_match_agnostic(self):
        forbidden = re.compile(
            r"(?i)(sturm|hearts|fenerbah|galatasaray|besiktas|beşiktaş|trabzon|2026[-_]0[1-9][-_][0-9]{2})"
        )
        for path in (BOOTSTRAP, RUNNER):
            self.assertTrue(path.exists(), path)
            self.assertIsNone(forbidden.search(path.read_text(encoding="utf-8")), path)

    def test_bootstrap_discovers_supported_termux_checkouts_and_pins_branch(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn('$HOME/hp/repos/hpfa', text)
        self.assertIn('$HOME/hpfa_claim_integrity/hpfa', text)
        self.assertIn('work/reconstruct-183-research-hardened-v1', text)
        self.assertIn('run_active_match_provider_metric_dictionary_v1.sh', text)
        self.assertIn('merge --ff-only', text)
        self.assertIn('remote_head_mismatch', text)

    def test_bootstrap_validates_origin_before_fetch(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        origin_guard = 'product_repo_origin_mismatch_before_fetch'
        fetch_cmd = 'git -C "$REPO" fetch origin "$BRANCH"'
        self.assertIn(origin_guard, text)
        self.assertIn(fetch_cmd, text)
        self.assertLess(text.index(origin_guard), text.index(fetch_cmd))

    def test_runner_enforces_runtime_and_phone_authority(self):
        text = RUNNER.read_text(encoding="utf-8")
        for token in (
            'runtime/active_single_match/current',
            'nested_phone_output_directory_rejected',
            '/sdcard/Download/HPFA',
            '/storage/emulated/0/Download/HPFA',
            'execution_identity_mismatch',
            'product_repo_origin_mismatch',
            'HPFA_183_ACTIVE_MATCH_',
            'ONE_ZIP_ONLY',
        ):
            self.assertIn(token, text)

    def test_runner_rejects_empty_active_match_inventory(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn('supported_file_count=int(inv.get("supported_file_count") or 0)', text)
        self.assertIn('unique_content_file_count=int(inv.get("unique_content_file_count") or 0)', text)
        self.assertIn('and supported_file_count > 0', text)
        self.assertIn('and unique_content_file_count > 0', text)

    def test_runner_preserves_claim_boundaries(self):
        text = RUNNER.read_text(encoding="utf-8")
        for token in (
            'provider_definition_inferred_from_active_match',
            'provider_candidate_is_validated_provider_identity',
            'metric_value_output_allowed',
            'comparison_allowed',
            'claim_allowed',
            'canonical_event_count',
            'UNKNOWN',
            'production_release',
        ):
            self.assertIn(token, text)
        command_pattern = re.compile(
            r"(?m)^\s*(?:pytest\b|python\s+-m\s+(?:pytest|unittest)\b)"
        )
        self.assertIsNone(command_pattern.search(text))

    def test_runner_binds_inventory_authority_without_inventing_provider_truth(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn('multiformat_file_inventory.py', text)
        self.assertIn('provider_metric_dictionary_lite.py', text)
        self.assertIn('INVENTORY_AUTHORITY_PLUS_PROVIDER_DICTIONARY_ADMISSION', text)
        self.assertIn('Provider metric semantics remain candidate/reference-only', text)


if __name__ == "__main__":
    unittest.main()
