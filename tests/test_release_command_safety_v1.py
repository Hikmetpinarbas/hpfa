from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "tools" / "hpfa-release.sh"
WRAPPER = ROOT / "tools" / "hpfa-release-wrapper.sh"


def test_legacy_release_command_is_fail_closed_and_non_mutating() -> None:
    text = RELEASE.read_text(encoding="utf-8")
    assert "Legacy HPFA release command is disabled" in text
    assert "exit 64" in text
    assert "git tag" not in text
    assert "git push" not in text
    assert "production_release=true" not in text.lower()


def test_release_wrapper_only_delegates_to_blocked_command() -> None:
    text = WRAPPER.read_text(encoding="utf-8")
    assert "hpfa-release.sh" in text
    assert "git " not in text
