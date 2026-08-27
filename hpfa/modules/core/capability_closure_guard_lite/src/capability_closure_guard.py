from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable

MODULE_ID = "capability_closure_guard_lite_v1"
CLAIM_SAFETY = "PRODUCT_CLOSURE_EVIDENCE_ONLY"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
PRODUCTION_RELEASE = False

DECISIONS = {
    "ACTIVE_CONTRACT",
    "ORPHAN_CONTRACT",
    "UNBOUND_IMPLEMENTATION",
    "TEST_ONLY_SURFACE",
    "SUPERSEDED_CONTRACT",
}

GOVERNANCE_MATRIX = Path("docs/governance/runtime_pack_v1/module_governance_matrix.tsv")
SOURCE_ROLE_REGISTRY = Path("docs/governance/runtime_pack_v1/source_role_registry.json")
RELEASE_STATUS_NORMALIZER = Path("docs/governance/runtime_pack_v1/release_status_normalizer.json")
CONTRACT_ROOT = Path("docs/contracts")
MODULE_ROOT = Path("hpfa/modules")
SPINE_RUNNER = Path("hpfa/modules/core/active_match_spine_runner/src/spine_runner.py")
ROOT_SPINE_ENTRYPOINT = Path("active_match_spine_runner.py")

IGNORED_PARTS = {
    ".git",
    "__pycache__",
    "archive",
    "archives",
    "donor",
    "donors",
    "fixtures",
    "reference_only",
}
CONTRACT_SECTION_HEADINGS = {"product node", "reused producers"}
PASS_STATUSES = {"PASS", "ACTIVE_MATCH_EVIDENCE_PASS"}


class ClosureGuardError(ValueError):
    pass


def normalize_capability_id(value: str) -> str:
    text = str(value or "").strip().casefold()
    text = re.sub(r"\bv(?:ersion)?\s*\d+\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _json(path: Path) -> dict[str, Any]:
    raw = json.loads(_read_text(path))
    if not isinstance(raw, dict):
        raise ClosureGuardError(f"json_object_required:{path.as_posix()}")
    return raw


def validate_governance_inputs(root: Path) -> dict[str, Any]:
    matrix_path = root / GOVERNANCE_MATRIX
    source_role_path = root / SOURCE_ROLE_REGISTRY
    release_path = root / RELEASE_STATUS_NORMALIZER
    for path in (matrix_path, source_role_path, release_path):
        if not path.is_file():
            raise ClosureGuardError(
                f"required_governance_input_missing:{path.relative_to(root).as_posix()}"
            )

    source_roles = _json(source_role_path)
    role_names = {
        str(item.get("role") or "")
        for item in source_roles.get("source_roles", [])
        if isinstance(item, dict)
    }
    if "ACTIVE_MATCH_RUNTIME_AUTHORITY" not in role_names or "GITHUB_PRODUCT_REPO" not in role_names:
        raise ClosureGuardError("source_role_registry_required_roles_missing")

    release = _json(release_path)
    statuses = {
        str(item.get("status") or "")
        for item in release.get("statuses", [])
        if isinstance(item, dict)
    }
    required_statuses = {
        "SMOKE_PASS",
        "ACTIVE_MATCH_EVIDENCE_PASS",
        "PRODUCTION_RELEASE",
        "RELEASE_CANDIDATE_NOT_PRODUCTION_BOUND",
    }
    if not required_statuses.issubset(statuses):
        raise ClosureGuardError("release_status_normalizer_required_statuses_missing")

    return {
        "module_governance_matrix": GOVERNANCE_MATRIX.as_posix(),
        "source_role_registry": SOURCE_ROLE_REGISTRY.as_posix(),
        "release_status_normalizer": RELEASE_STATUS_NORMALIZER.as_posix(),
        "matrix_is_discovery_seed_only": True,
    }


def load_governance_seed(root: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with (root / GOVERNANCE_MATRIX).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            raw_id = str(row.get("module_id") or "").strip()
            if not raw_id:
                continue
            cid = normalize_capability_id(raw_id)
            rows[cid] = {
                "display_name": raw_id,
                "current_status_hint": str(row.get("current_status") or "").strip(),
                "runtime_dependency_hint": str(row.get("runtime_dependency") or "").strip(),
                "release_evidence_required_hint": str(
                    row.get("release_evidence_required") or ""
                ).strip(),
            }
    return rows


def _contract_direct_id(path: Path) -> str:
    stem = re.sub(r"_v\d+$", "", path.stem, flags=re.IGNORECASE)
    return normalize_capability_id(stem)


def _explicit_contract_section_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    active = False
    for line in text.splitlines():
        if line.startswith("## "):
            heading = line[3:].strip().casefold()
            active = heading in CONTRACT_SECTION_HEADINGS
            continue
        if not active:
            continue
        stripped = line.strip().strip("`").strip()
        if not stripped or stripped.startswith("#"):
            continue
        candidate = normalize_capability_id(stripped.split("/")[-1])
        if candidate:
            tokens.add(candidate)
    return tokens


def discover_contracts(
    root: Path,
    known_capabilities: set[str],
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    contract_root = root / CONTRACT_ROOT
    if not contract_root.is_dir():
        return result
    for path in sorted(contract_root.glob("*.md")):
        relative = path.relative_to(root).as_posix()
        text = _read_text(path)
        direct = _contract_direct_id(path)
        has_product_node = bool(re.search(r"(?mi)^##\s+Product Node\s*$", text))
        if direct in known_capabilities or has_product_node:
            result.setdefault(direct, []).append(relative)
        for token in _explicit_contract_section_tokens(text):
            if token in known_capabilities or has_product_node:
                result.setdefault(token, []).append(relative)
    return {key: sorted(set(value)) for key, value in sorted(result.items())}


def discover_implementations(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    module_root = root / MODULE_ROOT
    if not module_root.is_dir():
        return result
    for module_dir in sorted(path for path in module_root.glob("*/*") if path.is_dir()):
        src = module_dir / "src"
        if not src.is_dir():
            continue
        py_files = sorted(path for path in src.rglob("*.py") if path.is_file())
        if not py_files:
            continue
        cid = normalize_capability_id(module_dir.name)
        hashes: dict[str, list[str]] = {}
        leaves: set[str] = set()
        for path in py_files:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            hashes.setdefault(digest, []).append(path.relative_to(root).as_posix())
            if path.stem != "__init__":
                leaves.add(path.stem)
        result[cid] = {
            "module_dir": module_dir.relative_to(root).as_posix(),
            "implementation_paths": [
                sorted(paths)[0]
                for _, paths in sorted(hashes.items(), key=lambda item: item[0])
            ],
            "reflection_groups": [
                sorted(paths) for paths in hashes.values() if len(paths) > 1
            ],
            "import_leaves": sorted(leaves),
        }
    return result


def _iter_python_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.py"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        lowered = {part.casefold() for part in relative.parts}
        if lowered & IGNORED_PARTS:
            continue
        yield path


def _is_test_path(relative: Path) -> bool:
    return (
        "tests" in {part.casefold() for part in relative.parts}
        or relative.name.startswith("test_")
    )


def _imports_leaf(text: str, leaves: Iterable[str]) -> bool:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    leaf_set = set(leaves)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[-1] in leaf_set:
                    return True
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[-1] in leaf_set:
                return True
    return False


def discover_consumers_and_tests(
    root: Path,
    implementations: dict[str, dict[str, Any]],
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    consumers: dict[str, list[str]] = {cid: [] for cid in implementations}
    tests: dict[str, list[str]] = {cid: [] for cid in implementations}
    python_files = list(_iter_python_files(root))
    for cid, info in implementations.items():
        module_dir = Path(str(info["module_dir"]))
        leaves = list(info.get("import_leaves") or [])
        for path in python_files:
            relative = path.relative_to(root)
            text = _read_text(path)
            imports = _imports_leaf(text, leaves)
            if _is_test_path(relative):
                if module_dir in relative.parents or imports:
                    tests[cid].append(relative.as_posix())
                continue
            if module_dir in relative.parents:
                continue
            if imports:
                consumers[cid].append(relative.as_posix())
    return (
        {key: sorted(set(value)) for key, value in consumers.items()},
        {key: sorted(set(value)) for key, value in tests.items()},
    )


def _path_literals_from_assignments(text: str, names: set[str]) -> set[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    found: set[str] = set()
    for node in tree.body:
        target_name: str | None = None
        value: ast.AST | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target_name = node.targets[0].id
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name = node.target.id
            value = node.value
        if target_name not in names or value is None:
            continue
        for child in ast.walk(value):
            if (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Name)
                and child.func.id == "Path"
                and child.args
                and isinstance(child.args[0], ast.Constant)
                and isinstance(child.args[0].value, str)
            ):
                found.add(child.args[0].value)
    return found


def discover_runtime_bindings(
    root: Path,
    implementations: dict[str, dict[str, Any]],
) -> dict[str, list[str]]:
    bindings: dict[str, list[str]] = {cid: [] for cid in implementations}
    spine_path = root / SPINE_RUNNER
    spine_text = _read_text(spine_path) if spine_path.is_file() else ""
    allowed = _path_literals_from_assignments(
        spine_text,
        {"ROLE_RESOLVER_DEPENDENCY_SURFACES", "ALLOWED_RUNTIME_SURFACES"},
    )
    for cid, info in implementations.items():
        module_dir = str(info.get("module_dir") or "")
        if module_dir in allowed:
            bindings[cid].append(
                f"{SPINE_RUNNER.as_posix()}:ALLOWED_RUNTIME_SURFACES"
            )

    spine_id = "active_match_spine_runner"
    root_entry = root / ROOT_SPINE_ENTRYPOINT
    if spine_id in implementations and root_entry.is_file():
        text = _read_text(root_entry)
        if _imports_leaf(text, {"spine_runner"}) and "run_spine_check" in text:
            bindings[spine_id].append(
                f"{ROOT_SPINE_ENTRYPOINT.as_posix()}:run_spine_check"
            )
    return {key: sorted(set(value)) for key, value in bindings.items()}


def current_product_tree_sha(root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD^{tree}"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ClosureGuardError("current_product_tree_sha_unavailable") from exc
    value = completed.stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ClosureGuardError("current_product_tree_sha_invalid")
    return value


def _derive_spine_capabilities(artifact: dict[str, Any]) -> dict[str, bool]:
    if (
        artifact.get("status") != "PASS"
        or artifact.get("active_match_authority_validated") is not True
    ):
        return {}
    result = {"active_match_spine_runner": True}
    policy = artifact.get("runtime_surface_policy") or {}
    executed = set(policy.get("executed_runtime_surfaces") or [])
    resolver_path = "hpfa/modules/core/content_source_role_resolver_lite"
    manifest_path = "hpfa/modules/core/canonical_ingest_surface_manifest"
    role = artifact.get("source_role_resolution") or {}
    manifest = artifact.get("surface_manifest") or {}
    if resolver_path in executed and role.get("status") == "PASS":
        result["content_source_role_resolver_lite"] = True
    if manifest_path in executed and manifest.get("status") == "PASS":
        result["canonical_ingest_surface_manifest"] = True
    return result


def load_active_match_evidence(
    evidence_path: Path | None,
    current_tree_sha: str,
) -> tuple[dict[str, bool], dict[str, Any]]:
    if evidence_path is None:
        return {}, {
            "status": "NOT_SUPPLIED",
            "path": None,
            "current_product_tree_sha": current_tree_sha,
        }
    evidence = _json(evidence_path)
    if evidence.get("evidence_kind") != "ACTIVE_MATCH_RUNTIME_EVIDENCE":
        raise ClosureGuardError("active_match_evidence_kind_invalid")
    if evidence.get("input_authority") != "ACTIVE_MATCH_RUNTIME_AUTHORITY":
        raise ClosureGuardError("active_match_evidence_authority_invalid")
    if str(evidence.get("product_tree_sha") or "") != current_tree_sha:
        raise ClosureGuardError("active_match_evidence_product_tree_mismatch")
    if evidence.get("canonical_event_count") != "UNKNOWN":
        raise ClosureGuardError("active_match_evidence_canonical_event_count_promoted")
    if evidence.get("true_action_count") != "UNKNOWN":
        raise ClosureGuardError("active_match_evidence_true_action_count_promoted")
    if evidence.get("production_release") is not False:
        raise ClosureGuardError("active_match_evidence_production_release_promoted")

    admitted: dict[str, bool] = {}
    explicit = evidence.get("capabilities")
    if isinstance(explicit, dict):
        for raw_id, record in sorted(explicit.items()):
            if not isinstance(record, dict):
                continue
            cid = normalize_capability_id(str(raw_id))
            admitted[cid] = bool(
                record.get("executed") is True
                and record.get("runtime_binding_validated") is True
                and str(record.get("status") or "").upper() in PASS_STATUSES
            )

    spine_artifact = evidence.get("active_match_spine_check")
    if isinstance(spine_artifact, dict):
        admitted.update(_derive_spine_capabilities(spine_artifact))

    return admitted, {
        "status": "ADMITTED",
        "path": evidence_path.as_posix(),
        "product_tree_sha": current_tree_sha,
    }


def _successor_from_hint(status_hint: str) -> str | None:
    match = re.fullmatch(r"SUPERSEDED_BY_(.+)", status_hint.strip().upper())
    return normalize_capability_id(match.group(1)) if match else None


def classify(
    *,
    contract: bool,
    implementation: bool,
    non_test_consumer: bool,
    test: bool,
    runtime_binding: bool,
    active_match_evidence: bool,
    superseded: bool,
) -> tuple[str, list[str]]:
    if superseded:
        return "SUPERSEDED_CONTRACT", ["current_successor_implementation_confirmed"]
    if contract and not implementation:
        return "ORPHAN_CONTRACT", ["contract_without_current_implementation"]
    if implementation and test and not non_test_consumer and not runtime_binding:
        return "TEST_ONLY_SURFACE", [
            "implementation_reachable_only_from_test_or_ci_surface"
        ]
    if all(
        (
            contract,
            implementation,
            non_test_consumer,
            test,
            runtime_binding,
            active_match_evidence,
        )
    ):
        return "ACTIVE_CONTRACT", ["six_link_closure_confirmed"]
    if implementation:
        missing = [
            name
            for name, present in (
                ("contract", contract),
                ("non_test_consumer", non_test_consumer),
                ("test", test),
                ("runtime_binding", runtime_binding),
                ("active_match_evidence", active_match_evidence),
            )
            if not present
        ]
        return "UNBOUND_IMPLEMENTATION", [f"missing:{name}" for name in missing]
    raise ClosureGuardError("unclassifiable_candidate_without_contract_or_implementation")


def build_report(
    root: str | Path,
    *,
    active_match_evidence_path: str | Path | None = None,
) -> dict[str, Any]:
    repo_root = Path(root).expanduser().resolve()
    if not repo_root.is_dir():
        raise ClosureGuardError(f"repo_root_missing:{repo_root}")

    governance = validate_governance_inputs(repo_root)
    seed = load_governance_seed(repo_root)
    implementations = discover_implementations(repo_root)
    known_capabilities = set(seed) | set(implementations)
    contracts = discover_contracts(repo_root, known_capabilities)
    consumers, tests = discover_consumers_and_tests(repo_root, implementations)
    runtime_bindings = discover_runtime_bindings(repo_root, implementations)
    tree_sha = current_product_tree_sha(repo_root)
    active_evidence, active_meta = load_active_match_evidence(
        Path(active_match_evidence_path).expanduser().resolve()
        if active_match_evidence_path is not None
        else None,
        tree_sha,
    )

    candidates = sorted(set(seed) | set(contracts) | set(implementations))
    records: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for cid in candidates:
        contract_paths = contracts.get(cid, [])
        implementation_info = implementations.get(cid)
        status_hint = str(seed.get(cid, {}).get("current_status_hint") or "")
        successor = _successor_from_hint(status_hint)
        successor_impl = implementations.get(successor or "") if successor else None
        superseded = bool(successor and successor_impl and contract_paths)

        contract = bool(contract_paths)
        implementation = implementation_info is not None
        non_test_consumer_paths = consumers.get(cid, [])
        test_paths = tests.get(cid, [])
        runtime_binding_paths = runtime_bindings.get(cid, [])
        active = bool(active_evidence.get(cid, False))

        if not contract and not implementation and not superseded:
            skipped.append(
                {
                    "capability_id": cid,
                    "reason": "seed_only_without_contract_or_implementation",
                }
            )
            continue

        decision, reason_codes = classify(
            contract=contract,
            implementation=implementation,
            non_test_consumer=bool(non_test_consumer_paths),
            test=bool(test_paths),
            runtime_binding=bool(runtime_binding_paths),
            active_match_evidence=active,
            superseded=superseded,
        )
        if decision not in DECISIONS:
            raise ClosureGuardError(f"unknown_decision:{decision}")

        records.append(
            {
                "capability_id": cid,
                "display_name": seed.get(cid, {}).get("display_name") or cid,
                "evidence": {
                    "contract": contract,
                    "implementation": implementation,
                    "non_test_consumer": bool(non_test_consumer_paths),
                    "test": bool(test_paths),
                    "runtime_binding": bool(runtime_binding_paths),
                    "active_match_evidence": active,
                },
                "evidence_paths": {
                    "contract": contract_paths,
                    "implementation": (implementation_info or {}).get(
                        "implementation_paths", []
                    ),
                    "non_test_consumer": non_test_consumer_paths,
                    "test": test_paths,
                    "runtime_binding": runtime_binding_paths,
                },
                "reflection_groups": (implementation_info or {}).get(
                    "reflection_groups", []
                ),
                "superseded_by": successor if superseded else None,
                "decision": decision,
                "reason_codes": reason_codes,
                "governance_status_hint": status_hint or None,
                "governance_status_used_as_truth": False,
            }
        )

    return {
        "guard_id": MODULE_ID,
        "status": "PASS",
        "claim_safety": CLAIM_SAFETY,
        "repo_root": str(repo_root),
        "product_tree_sha": tree_sha,
        "governance_inputs": governance,
        "active_match_evidence_input": active_meta,
        "classification_order": [
            "SUPERSEDED_CONTRACT",
            "ORPHAN_CONTRACT",
            "TEST_ONLY_SURFACE",
            "ACTIVE_CONTRACT",
            "UNBOUND_IMPLEMENTATION",
        ],
        "capability_count": len(records),
        "capabilities": records,
        "unclassified_seed_candidates": skipped,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": PRODUCTION_RELEASE,
    }


def render_summary(report: dict[str, Any]) -> str:
    lines = [
        "HPFA CAPABILITY CLOSURE GUARD LITE V1",
        "=====================================",
        f"status={report.get('status')}",
        f"product_tree_sha={report.get('product_tree_sha')}",
        f"capability_count={report.get('capability_count')}",
        f"canonical_event_count={report.get('canonical_event_count')}",
        f"true_action_count={report.get('true_action_count')}",
        f"production_release={str(report.get('production_release')).lower()}",
        "",
    ]
    for record in report.get("capabilities", []):
        evidence = record.get("evidence") or {}
        bits = ",".join(
            f"{key}={str(bool(evidence.get(key))).lower()}"
            for key in (
                "contract",
                "implementation",
                "non_test_consumer",
                "test",
                "runtime_binding",
                "active_match_evidence",
            )
        )
        lines.append(
            f"{record.get('capability_id')} | {record.get('decision')} | {bits}"
        )
    return "\n".join(lines) + "\n"


def write_report(
    root: str | Path,
    out_dir: str | Path,
    *,
    active_match_evidence_path: str | Path | None = None,
) -> dict[str, Any]:
    report = build_report(
        root,
        active_match_evidence_path=active_match_evidence_path,
    )
    output_root = Path(out_dir).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "capability_closure_guard_lite_v1.json"
    txt_path = output_root / "capability_closure_guard_lite_v1.txt"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    txt_path.write_text(render_summary(report), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit HPFA capability closure without executing ACTIVE_MATCH."
    )
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[5]))
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--active-match-evidence")
    args = parser.parse_args()
    report = write_report(
        args.root,
        args.out_dir,
        active_match_evidence_path=args.active_match_evidence,
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "capability_count": report["capability_count"],
                "canonical_event_count": report["canonical_event_count"],
                "true_action_count": report["true_action_count"],
                "production_release": report["production_release"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
