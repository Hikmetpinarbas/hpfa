import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]


CURRENT_AUTHORITY_FILES = [
    ROOT / "README.md",
    ROOT / "docs/governance/HPFA_MASTER_PROJECT_DIRECTIVE_SHORT_CURRENT.md",
    ROOT / "docs/governance/HPFA_OPERATOR_HANDOFF_CURRENT.md",
    ROOT / "docs/governance/HPFA_NORTH_STAR_RECENTERING_PROMPT_V1.md",
    ROOT / "docs/governance/HPFA_NEW_PAGE_CONTINUITY_HANDOFF_PROMPT_V1.md",
    ROOT / "docs/governance/HPFA_PRODUCT_ARCHITECT_EVOLUTION_ENGINE_DIRECTIVE_V1.md",
    ROOT / "docs/governance/product_architect_evolution_protocol_v1.md",
    ROOT / "docs/prompts/HPFA_PROJECT_LOGBOOK_PROMPT.md",
    ROOT / "docs/brand/HPFA_BRAND_IDENTITY_CORE_LAYER.md",
]

FORBIDDEN_POSITIVE_AUTHORITY_PHRASES = [
    "hpfa is an event-only",
    "long-lived event-only football intelligence product",
    "best event-only platform",
    "event-only eligibility gate",
    "only ideas eventually implementable with event data are eligible",
    "yalnızca event data ile uygulanabilecek",
]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8").casefold()


def test_current_authority_declares_zfgv_not_event_only_product():
    for path in CURRENT_AUTHORITY_FILES:
        assert path.exists(), path
        text = _text(path)
        for phrase in FORBIDDEN_POSITIVE_AUTHORITY_PHRASES:
            assert phrase.casefold() not in text, f"{path}: {phrase}"

    master = _text(ROOT / "docs/governance/HPFA_MASTER_PROJECT_DIRECTIVE_SHORT_CURRENT.md")
    handoff = _text(ROOT / "docs/governance/HPFA_OPERATOR_HANDOFF_CURRENT.md")

    assert "zenginleştirilmiş futbol gözlem verisi" in master
    assert "product-wide observation ceiling" in master
    assert "must not be used as a binary reason to suppress" in master
    assert "global `event_only_compatible=true/false` must not be the sole executable capability gate" in master

    assert "event ⊂ zfgv" in handoff
    assert "event is one observation family, not the whole observation universe" in handoff


def test_metric_registry_uses_zfgv_observation_model():
    registry = json.loads((ROOT / "configs/metrics/metric_registry_v1.json").read_text(encoding="utf-8"))
    assert registry["observation_model"] == "ZFGV_V1"
    for metric in registry.get("metrics", []):
        assert "required_observation_capabilities" in metric
        assert "required_observation_layers" in metric
        assert "event_only_compatible" not in metric


def test_legacy_eventonly_allowlist_has_zero_product_authority():
    policy = json.loads(
        (ROOT / "hpfa/modules/core/metric_fusion_engine/policies/eventonly_metric_allowlist_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert policy["status"] == "legacy_compatibility_not_product_authority"
    assert policy["product_wide_admission_authority"] is False
    assert policy["construct_eligibility_authority"] is False
    assert policy["can_veto_non_event_zfgv_construct"] is False


def test_metric_fusion_scaffold_is_zfgv_not_global_event_gate():
    text = _text(ROOT / "hpfa/modules/core/metric_fusion_engine/README.md")
    assert "# hpfa zfgv metric fusion engine v1" in text
    assert "global event-only or event-surface allowlist must never authorize or veto zfgv product admission" in text


def test_reasoning_and_progression_plans_do_not_make_event_shape_universal():
    reasoning = _text(ROOT / "docs/contracts/reasoning_grammar_spine_lite_v1.md")
    progression = _text(ROOT / "docs/HPFA_GITHUB_PROGRESSION_ENGINE_CONTRACTS_PLAN_V1.md")
    action_cost = _text(ROOT / "docs/contracts/action_value_cost_fusion_lite_v1.md")

    assert "action/event is one possible observation family" in reasoning
    assert "progression is a football construct, not an event-only construct" in progression
    assert "no global event-surface gate may veto a construct that does not require action/event evidence" in action_cost
