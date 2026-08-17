from __future__ import annotations

import os
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

    def test_runtime_tools_are_executable(self):
        for path in (BOOTSTRAP, RUNNER):
            self.assertTrue(os.access(path, os.X_OK), path)

    def test_bootstrap_discovers_supported_termux_checkouts_and_pins_branch(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn('$HOME/hp/repos/hpfa', text)
        self.assertIn('$HOME/hpfa_claim_integrity/hpfa', text)
        self.assertIn('work/reconstruct-183-research-hardened-v1', text)
        self.assertIn('run_active_match_provider_metric_dictionary_v1.sh', text)
        self.assertIn('merge --ff-only', text)
        self.assertIn('remote_head_mismatch', text)

    def test_bootstrap_trust_boundary_precedes_status_and_fetch(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn('core.fsmonitor=false', text)
        self.assertIn('core.hooksPath=/dev/null', text)
        self.assertIn('product_repo_origin_transport_or_identity_rejected', text)
        self.assertNotIn('http://github.com/', text)
        origin_guard = text.index('product_repo_origin_transport_or_identity_rejected')
        status = text.index('status --porcelain --untracked-files=all')
        fetch = text.index('clean_fetch_git --git-dir="$FETCH_REPO" fetch --no-tags --no-recurse-submodules')
        self.assertLess(origin_guard, status)
        self.assertLess(origin_guard, fetch)

    def test_runner_enforces_runtime_and_phone_authority(self):
        text = RUNNER.read_text(encoding="utf-8")
        for token in (
            'runtime/active_single_match/current',
            'nested_phone_output_directory_rejected',
            '/sdcard/Download/HPFA',
            '/storage/emulated/0/Download/HPFA',
            'execution_identity_mismatch',
            'HPFA_183_ACTIVE_MATCH_',
            'ONE_ZIP_ONLY',
        ):
            self.assertIn(token, text)

    def test_runner_rejects_untracked_ignored_and_empty_active_match_inventory(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn('status --porcelain --untracked-files=all --ignored=matching', text)
        self.assertNotIn('--untracked-files=no', text)
        self.assertIn('core.fsmonitor=false', text)
        self.assertIn('core.hooksPath=/dev/null', text)
        self.assertIn('supported_file_count=int(inv.get("supported_file_count") or 0)', text)
        self.assertIn('unique_content_file_count=int(inv.get("unique_content_file_count") or 0)', text)
        self.assertIn('and supported_file_count > 0', text)
        self.assertIn('and unique_content_file_count > 0', text)

    def test_runner_accepts_valid_linked_worktree_gitfiles(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertNotIn('[[ -d "$REPO/.git" ]]', text)
        self.assertIn('rev-parse --is-inside-work-tree', text)
        self.assertIn('rev-parse --git-dir', text)
        self.assertIn('product_repo_git_dir_unresolved', text)

    def test_runner_isolates_core_worktree_and_git_environment_before_root_check(self):
        text = RUNNER.read_text(encoding="utf-8")
        for token in (
            '-u GIT_DIR',
            '-u GIT_WORK_TREE',
            '-u GIT_COMMON_DIR',
            '-u GIT_CONFIG_COUNT',
            '-u GIT_CONFIG_PARAMETERS',
            'GIT_CONFIG_NOSYSTEM=1',
            'GIT_CONFIG_GLOBAL=/dev/null',
            'config --show-origin --get-all core.worktree',
            'product_repo_core_worktree_override_rejected',
        ):
            self.assertIn(token, text)
        core_worktree_guard = text.index('product_repo_core_worktree_override_rejected')
        root_resolution = text.index('rev-parse --show-toplevel')
        origin_guard = text.index('product_repo_origin_transport_or_identity_rejected')
        execution_cd = text.index('\ncd "$REPO_RESOLVED"\n')
        self.assertLess(core_worktree_guard, root_resolution)
        self.assertLess(core_worktree_guard, origin_guard)
        self.assertLess(core_worktree_guard, execution_cd)

    def test_runner_requires_repo_to_be_exact_worktree_root(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn('rev-parse --show-toplevel', text)
        self.assertIn('REPO_RESOLVED=', text)
        self.assertIn('WORKTREE_TOP_RESOLVED=', text)
        self.assertIn('product_repo_worktree_root_mismatch', text)
        root_guard = text.index('product_repo_worktree_root_mismatch')
        origin_guard = text.index('product_repo_origin_transport_or_identity_rejected')
        execution_cd = text.index('\ncd "$REPO_RESOLVED"\n')
        self.assertLess(root_guard, origin_guard)
        self.assertLess(root_guard, execution_cd)

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
