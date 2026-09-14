from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / 'src' / 'full_system_match_diagnostic_harness.py'


def _load_module():
    spec = importlib.util.spec_from_file_location('hpfa_full_system_match_diagnostic_harness_test', MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_pytest_summary() -> None:
    module = _load_module()
    assert module._parse_pytest_summary('775 passed, 3 skipped in 12.40s') == {
        'passed': 775,
        'failed': 0,
        'skipped': 3,
        'errors': 0,
    }
    assert module._parse_pytest_summary('2 failed, 8 passed, 1 error in 1.2s') == {
        'passed': 8,
        'failed': 2,
        'skipped': 0,
        'errors': 1,
    }


def test_apply_engineering_states_keeps_runtime_and_test_truth_separate() -> None:
    module = _load_module()
    diagnostic = {
        'component_coverage': [
            {
                'component': 'c4_fusion',
                'runtime_execution_state': 'EXECUTED',
                'engineering_test_state': 'UNKNOWN',
                'result_state': 'PASS',
                'output_artifact': 'active_match_full_spine_v1.json:intelligence_chains',
            },
            {
                'component': 'tracking_video_pipeline',
                'runtime_execution_state': 'NOT_APPLICABLE',
                'engineering_test_state': 'UNKNOWN',
                'result_state': 'UNKNOWN',
                'output_artifact': None,
            },
        ]
    }
    engineering = {
        'module_states': [
            {
                'module': 'multi_signal_evidence_fusion_lite',
                'engineering_test_state': 'PASS',
            }
        ]
    }
    enriched = module.apply_engineering_states(diagnostic, engineering)
    fusion = enriched['component_coverage'][0]
    tracking = enriched['component_coverage'][1]
    assert fusion['runtime_execution_state'] == 'EXECUTED'
    assert fusion['engineering_test_state'] == 'PASS'
    assert fusion['result_state'] == 'PASS'
    assert tracking['runtime_execution_state'] == 'NOT_APPLICABLE'
    assert tracking['engineering_test_state'] == 'UNKNOWN'
    assert enriched['engineering_test_state_counts'] == {'PASS': 1, 'UNKNOWN': 1}


def test_junit_module_execution_distinguishes_pass_skip_and_fail(tmp_path: Path) -> None:
    module = _load_module()
    junit = tmp_path / 'junit.xml'
    junit.write_text(
        """<?xml version='1.0' encoding='utf-8'?>
<testsuites><testsuite tests='4'>
  <testcase classname='hpfa.modules.core.alpha.tests.test_a' name='test_pass' file='hpfa/modules/core/alpha/tests/test_a.py' />
  <testcase classname='hpfa.modules.core.alpha.tests.test_a' name='test_skip' file='hpfa/modules/core/alpha/tests/test_a.py'><skipped /></testcase>
  <testcase classname='hpfa.modules.core.beta.tests.test_b' name='test_fail' file='hpfa/modules/core/beta/tests/test_b.py'><failure /></testcase>
  <testcase classname='hpfa.modules.core.gamma.tests.test_c' name='test_error' file='hpfa/modules/core/gamma/tests/test_c.py'><error /></testcase>
</testsuite></testsuites>""",
        encoding='utf-8',
    )
    execution = module._junit_module_execution(junit)
    assert execution['alpha'] == {'test_case_count': 2, 'passed': 1, 'skipped': 1}
    assert execution['beta']['failed'] == 1
    assert execution['gamma']['errors'] == 1


def test_human_answer_pack_preserves_claim_ceiling() -> None:
    module = _load_module()
    diagnostic = {
        'match_football_intelligence': {
            'action_occurrence_structure': {'occurrence_candidates': 1256},
            'partial_order_sequences': {
                'sequence_candidates': 1961,
                'branch_maps': 673,
                'first_supported_divergence_candidates': 673,
            },
            'comparison': {
                'eligible_outcome_records': 3634,
                'comparable_counterevidence_candidates': 97,
                'process_variant_families': 76,
                'grammar_stable_mixed_outcome_families': 8,
            },
            'safe_findings': {
                'status_counts': {'DOWNGRADE': 100, 'EMIT': 0, 'ABSTAIN': 0},
                'professional_finding_emitted_count': 0,
            },
        },
        'gap_report': [{'smallest_path': 'close evidence sufficiency accounting'}],
        'top_defensible_process_mechanism_candidates': [],
    }
    answers = module._human_answers(diagnostic)
    assert len(answers) == 8
    joined = '\n'.join(answer for _, answer in answers)
    assert 'publishable tactical truth değildir' in joined
    assert 'professional EMIT=0' in joined
    assert 'coach intention' in joined
