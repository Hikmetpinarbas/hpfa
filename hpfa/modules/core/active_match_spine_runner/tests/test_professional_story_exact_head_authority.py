from pathlib import Path

import active_match_professional_story_run_v1 as runner


def test_canonical_full_spine_uses_product_checkout_but_validates_runtime_authority(monkeypatch, tmp_path: Path) -> None:
    product_root = tmp_path / "product"
    runtime_root = tmp_path / "runtime_authority"
    match_dir = runtime_root / runner.ACTIVE_MATCH_RELATIVE_PATH
    out_dir = tmp_path / "out"
    product_root.mkdir(parents=True)
    match_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)

    seen = {}

    class GitResult:
        returncode = 0
        stdout = "deadbeef\n"
        stderr = ""

    monkeypatch.setattr(runner.subprocess, "run", lambda *args, **kwargs: GitResult())

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

    class GitResult:
        returncode = 0
        stdout = "wrong-head\n"
        stderr = ""

    monkeypatch.setattr(runner.subprocess, "run", lambda *args, **kwargs: GitResult())

    called = {"main": False}

    def fake_main():
        called["main"] = True
        return 0

    monkeypatch.setattr(runner.canonical_runner, "main", fake_main)

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
    assert called["main"] is False


def test_no_sample_match_identity_leak() -> None:
    source = Path("active_match_professional_story_run_v1.py").read_text(encoding="utf-8")
    for token in ("Galatasaray", "Fenerbahce", "Fenerbahçe", "15.08.2026"):
        assert token not in source
