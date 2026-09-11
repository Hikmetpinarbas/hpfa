from pathlib import Path

import active_match_professional_story_run_v1 as runner


def _git_runner(head: str, status: str = ""):
    class GitResult:
        returncode = 0
        stderr = ""

        def __init__(self, stdout: str):
            self.stdout = stdout

    def run(command, *args, **kwargs):
        if command[:3] == ["git", "rev-parse", "HEAD"]:
            return GitResult(head + "\n")
        if command[:3] == ["git", "status", "--porcelain"]:
            return GitResult(status)
        return GitResult("")

    return run


def test_canonical_full_spine_uses_clean_exact_product_checkout_but_validates_runtime_authority(monkeypatch, tmp_path: Path) -> None:
    product_root = tmp_path / "product"
    runtime_root = tmp_path / "runtime_authority"
    match_dir = runtime_root / runner.ACTIVE_MATCH_RELATIVE_PATH
    out_dir = tmp_path / "out"
    product_root.mkdir(parents=True)
    match_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)

    seen = {}
    monkeypatch.setattr(runner.subprocess, "run", _git_runner("deadbeef"))

    def original_validate(path, authority_root):
        seen["validated_path"] = Path(path)
        seen["authority_root"] = Path(authority_root)
        return Path(path)

    monkeypatch.setattr(
        runner.canonical_runner.full_spine_module,
        "validate_active_match_authority",
        original_validate,
    )

    def fake_main():
        args = list(runner.sys.argv)
        seen["argv"] = args
        execution_root = Path(args[args.index("--execution-root") + 1])
        runner.canonical_runner.full_spine_module.validate_active_match_authority(
            match_dir,
            execution_root,
        )
        print('{"status":"REVIEW_REQUIRED"}')
        return 0

    monkeypatch.setattr(runner.canonical_runner, "main", fake_main)

    result = runner._run_canonical_full_spine(
        match_dir=match_dir,
        out_dir=out_dir,
        repo_root=product_root,
        runtime_authority_root=runtime_root,
        expected_product_commit="deadbeef",
    )

    assert result["passed"] is True
    assert result["product_execution_root"] == str(product_root)
    assert result["runtime_authority_root"] == str(runtime_root)
    assert result["product_commit_matches_expected"] is True
    assert result["product_worktree_clean"] is True
    assert result["exact_head_provenance_verified"] is True
    assert seen["authority_root"] == runtime_root
    assert seen["validated_path"] == match_dir
    assert Path(seen["argv"][seen["argv"].index("--execution-root") + 1]) == product_root


def test_commit_mismatch_fails_before_canonical_execution(monkeypatch, tmp_path: Path) -> None:
    product_root = tmp_path / "product"
    runtime_root = tmp_path / "runtime_authority"
    match_dir = runtime_root / runner.ACTIVE_MATCH_RELATIVE_PATH
    out_dir = tmp_path / "out"
    product_root.mkdir(parents=True)
    match_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)

    monkeypatch.setattr(runner.subprocess, "run", _git_runner("wrong-head"))
    called = {"main": False}
    monkeypatch.setattr(runner.canonical_runner, "main", lambda: called.__setitem__("main", True))

    result = runner._run_canonical_full_spine(
        match_dir=match_dir,
        out_dir=out_dir,
        repo_root=product_root,
        runtime_authority_root=runtime_root,
        expected_product_commit="expected-head",
    )

    assert result["passed"] is False
    assert result["returncode"] == 2
    assert result["product_commit_matches_expected"] is False
    assert result["exact_head_provenance_verified"] is False
    assert called["main"] is False


def test_missing_expected_commit_fails_before_canonical_execution(monkeypatch, tmp_path: Path) -> None:
    product_root = tmp_path / "product"
    runtime_root = tmp_path / "runtime_authority"
    match_dir = runtime_root / runner.ACTIVE_MATCH_RELATIVE_PATH
    out_dir = tmp_path / "out"
    product_root.mkdir(parents=True)
    match_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)
    monkeypatch.setattr(runner.subprocess, "run", _git_runner("deadbeef"))

    result = runner._run_canonical_full_spine(
        match_dir=match_dir,
        out_dir=out_dir,
        repo_root=product_root,
        runtime_authority_root=runtime_root,
        expected_product_commit=None,
    )

    assert result["passed"] is False
    assert "expected_product_commit_required" in result["stderr"]
    assert result["exact_head_provenance_verified"] is False


def test_dirty_checkout_fails_even_when_head_matches(monkeypatch, tmp_path: Path) -> None:
    product_root = tmp_path / "product"
    runtime_root = tmp_path / "runtime_authority"
    match_dir = runtime_root / runner.ACTIVE_MATCH_RELATIVE_PATH
    out_dir = tmp_path / "out"
    product_root.mkdir(parents=True)
    match_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)
    monkeypatch.setattr(runner.subprocess, "run", _git_runner("deadbeef", " M active_match_spine_runner.py\n"))

    result = runner._run_canonical_full_spine(
        match_dir=match_dir,
        out_dir=out_dir,
        repo_root=product_root,
        runtime_authority_root=runtime_root,
        expected_product_commit="deadbeef",
    )

    assert result["passed"] is False
    assert result["product_commit_matches_expected"] is True
    assert result["product_worktree_clean"] is False
    assert "product_worktree_not_clean" in result["stderr"]
    assert result["exact_head_provenance_verified"] is False


def test_match_dir_is_not_resolved_before_canonical_authority_validation() -> None:
    source = Path("active_match_professional_story_run_v1.py").read_text(encoding="utf-8")
    assert "Path(args.match_dir).expanduser().absolute()" in source
    assert "Path(args.match_dir).expanduser().resolve" not in source


def test_no_sample_match_identity_leak() -> None:
    source = Path("active_match_professional_story_run_v1.py").read_text(encoding="utf-8")
    for token in ("Galatasaray", "Fenerbahce", "Fenerbahçe", "15.08.2026"):
        assert token not in source