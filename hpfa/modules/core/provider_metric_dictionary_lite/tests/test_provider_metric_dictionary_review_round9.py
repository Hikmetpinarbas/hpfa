from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BOOTSTRAP = ROOT / "tools" / "bootstrap_termux_provider_metric_dictionary_v1.sh"
RUNNER = ROOT / "tools" / "run_active_match_provider_metric_dictionary_v1.sh"


class ProviderMetricDictionaryRuntimeHardeningRound9Tests(unittest.TestCase):
    def test_bootstrap_clears_inherited_command_scope_git_config_before_fetch(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        start = text.index("clean_fetch_git(){")
        fetch = text.index('clean_fetch_git --git-dir="$FETCH_REPO" fetch --no-tags --no-recurse-submodules')
        prefetch = text[start:fetch]
        self.assertIn("env -i", prefetch)
        self.assertIn("GIT_CONFIG_GLOBAL=/dev/null", prefetch)
        self.assertIn("GIT_CONFIG_SYSTEM=/dev/null", prefetch)
        self.assertIn("GIT_CONFIG_NOSYSTEM=1", prefetch)
        self.assertIn("http.sslVerify=true", prefetch)
        self.assertIn("protocol.ext.allow=never", prefetch)
        self.assertIn("GIT_CONFIG_COUNT/GIT_CONFIG_KEY_*/GIT_CONFIG_VALUE_*", text)
        self.assertIn("GIT_CONFIG_PARAMETERS", text)

    def test_runner_rejects_hidden_index_flags_before_cleanliness_and_execution(self):
        text = RUNNER.read_text(encoding="utf-8")
        for token in (
            "ls-files -v",
            "product_repo_index_visibility_query_failed",
            "product_repo_index_visibility_flags_rejected",
            "S|[a-z]",
        ):
            self.assertIn(token, text)
        guard = text.index("product_repo_index_visibility_flags_rejected")
        status = text.index("status --porcelain --untracked-files=all --ignored=matching")
        execution_cd = text.index('\ncd "$REPO_RESOLVED"\n')
        self.assertLess(guard, status)
        self.assertLess(guard, execution_cd)


if __name__ == "__main__":
    unittest.main()
