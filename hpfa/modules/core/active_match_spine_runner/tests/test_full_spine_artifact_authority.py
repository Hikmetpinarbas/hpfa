import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from full_spine_runner import (
    PROCESS_STORY_DIAGNOSTIC_ARTIFACT,
    PROCESS_STORY_PUBLICATION_AUTHORITY_ARTIFACT,
    _artifact_authority_projection,
)


def test_full_spine_mixed_artifact_inventory_is_never_publication_authority():
    artifacts = [
        f"/tmp/{PROCESS_STORY_DIAGNOSTIC_ARTIFACT}",
        f"/tmp/{PROCESS_STORY_PUBLICATION_AUTHORITY_ARTIFACT}",
        "/tmp/other_diagnostic.json",
    ]
    malicious_or_version_skewed_parent = {
        "current_invocation_artifacts_are_publication_authority": True,
        "process_story_diagnostic_user_facing_publication_authority": True,
        "process_story_publication_authority_artifact": PROCESS_STORY_DIAGNOSTIC_ARTIFACT,
    }

    projection = _artifact_authority_projection(malicious_or_version_skewed_parent, artifacts)

    assert projection["current_invocation_artifacts_are_publication_authority"] is False
    assert projection["process_story_diagnostic_artifact"] == PROCESS_STORY_DIAGNOSTIC_ARTIFACT
    assert projection["process_story_publication_authority_artifact"] == PROCESS_STORY_PUBLICATION_AUTHORITY_ARTIFACT
    assert projection["process_story_diagnostic_artifact_present_in_current_invocation"] is True
    assert projection["process_story_publication_authority_artifact_present_in_current_invocation"] is True
    assert projection["process_story_parent_authority_contract_preserved"] is False


def test_full_spine_records_when_parent_authority_contract_is_preserved():
    parent = {
        "current_invocation_artifacts_are_publication_authority": False,
        "process_story_diagnostic_user_facing_publication_authority": False,
        "process_story_publication_authority_artifact": PROCESS_STORY_PUBLICATION_AUTHORITY_ARTIFACT,
    }
    projection = _artifact_authority_projection(
        parent,
        [f"/tmp/{PROCESS_STORY_PUBLICATION_AUTHORITY_ARTIFACT}"],
    )

    assert projection["current_invocation_artifacts_are_publication_authority"] is False
    assert projection["process_story_diagnostic_artifact_present_in_current_invocation"] is False
    assert projection["process_story_publication_authority_artifact_present_in_current_invocation"] is True
    assert projection["process_story_parent_authority_contract_preserved"] is True
