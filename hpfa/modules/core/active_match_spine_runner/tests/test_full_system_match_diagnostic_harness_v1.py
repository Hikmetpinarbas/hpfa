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


def test_module_states_reuse_fail_local_execution_truth() -> None:
    module = _load_module()
    modules = [
        {'module': 'alpha', 'source_file_count': 1, 'test_file_count': 1, 'test_files': ['hpfa/modules/core/alpha/tests/test_a.py']},
        {'module': 'beta', 'source_file_count': 1, 'test_file_count': 1, 'test_files': ['hpfa/modules/core/beta/tests/test_b.py']},
        {'module': 'gamma', 'source_file_count': 1, 'test_file_count': 1, 'test_files': ['hpfa/modules/core/gamma/tests/test_c.py']},
        {'module': 'delta', 'source_file_count': 1, 'test_file_count': 0, 'test_files': []},
    ]
    audit = {
        'product_compile_status': 'PASS',
        'per_file_results': [
            {
                'test_file': 'hpfa/modules/core/alpha/tests/test_a.py',
                'returncode': 0,
                'tests': 2,
                'failures': 0,
                'errors': 0,
                'skipped': 1,
            },
            {
                'test_file': 'hpfa/modules/core/beta/tests/test_b.py',
                'returncode': 1,
                'tests': 1,
                'failures': 1,
                'errors': 0,
                'skipped': 0,
            },
        ],
    }
    rows = {row['module']: row for row in module._module_states_from_fail_local(modules, audit)}
    assert rows['alpha']['engineering_test_state'] == 'PASS'
    assert rows['alpha']['passed'] == 1
    assert rows['beta']['engineering_test_state'] == 'FAIL'
    assert rows['gamma']['engineering_test_state'] == 'UNKNOWN'
    assert rows['delta']['engineering_test_state'] == 'NO_TESTS'


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


def test_fail_local_monolithic_review_does_not_overwrite_isolated_pass() -> None:
    module = _load_module()
    modules = [
        {'module': 'alpha', 'source_file_count': 1, 'test_file_count': 1, 'test_files': ['hpfa/modules/core/alpha/tests/test_a.py']},
    ]
    audit = {
        'product_compile_status': 'PASS',
        'isolated_test_status': 'PASS',
        'monolithic_product_core_status': 'REVIEW_REQUIRED',
        'monolithic_state_contamination_classification': 'FULL_SUITE_STATE_OR_IMPORT_CONTAMINATION_CONFIRMED',
        'per_file_results': [
            {
                'test_file': 'hpfa/modules/core/alpha/tests/test_a.py',
                'returncode': 0,
                'tests': 1,
                'failures': 0,
                'errors': 0,
                'skipped': 0,
            }
        ],
    }
    rows = module._module_states_from_fail_local(modules, audit)
    assert rows[0]['engineering_test_state'] == 'PASS'


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
    assert 'match-local mekanizma incelemesini doğrudan zenginleştiriyor' in joined
    assert 'professional EMIT=0' in joined
    assert 'physical-state, intention ve causal construct' in joined
