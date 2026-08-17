from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
RUNNER = ROOT / "tools" / "run_active_match_provider_metric_dictionary_v1.sh"


class ProviderMetricDictionaryReviewRound10Tests(unittest.TestCase):
    def test_runner_isolates_python_environment_and_uses_trusted_interpreter(self):
        text = RUNNER.read_text(encoding="utf-8")
        for token in (
            'TRUSTED_PYTHON="/data/data/com.termux/files/usr/bin/python"',
            'safe_python(){',
            'env -i',
            '-u PYTHONPATH',
            '-u PYTHONHOME',
            '-u PYTHONSTARTUP',
            '-u PYTHONUSERBASE',
            '-u PYTHONINSPECT',
            'PYTHONNOUSERSITE=1',
            'trusted_python_interpreter_missing',
            'run_step inventory safe_python',
            'run_step provider_metric_dictionary safe_python',
            'safe_python - "$TMP_ROOT" "$ACTUAL_BRANCH"',
            'safe_python - "$TMP_ROOT" "$ZIP_TMP"',
        ):
            self.assertIn(token, text)

        self.assertNotRegex(text, re.compile(r"(?m)^\s*python\b"))
        self.assertNotRegex(text, re.compile(r"run_step\s+\w+\s+python\b"))
        self.assertNotIn('command -v python', text)

        guard = text.index('safe_python(){')
        first_runtime_python = text.index('run_step inventory safe_python')
        self.assertLess(guard, first_runtime_python)


if __name__ == "__main__":
    unittest.main()
