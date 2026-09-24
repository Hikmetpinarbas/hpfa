from __future__ import annotations

import argparse
import hashlib
import json
import re
import tomllib
import zipfile
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dependency_name(spec: str) -> str:
    return re.split(r"[<>=!~\[ ;]", spec, maxsplit=1)[0].strip().lower()


def audit(repo: Path, wheel: Path) -> dict:
    pyproject = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    dependency_policy = json.loads(
        (repo / "release/release_dependency_policy_v1.json").read_text(encoding="utf-8")
    )
    bundle_policy = json.loads(
        (repo / "release/release_bundle_policy_v1.json").read_text(encoding="utf-8")
    )
    project = pyproject["project"]
    optional = project.get("optional-dependencies") or {}
    mandatory = list(project.get("dependencies") or [])

    declared_optional = {
        dependency_name(spec): {"scope": scope, "specifier": spec}
        for scope, specs in optional.items()
        for spec in specs
    }
    policy_optional = dependency_policy.get("optional_dependencies") or {}
    undeclared_policy = sorted(set(policy_optional) - set(declared_optional))
    missing_policy = sorted(set(declared_optional) - set(policy_optional))

    with zipfile.ZipFile(wheel) as z:
        names = sorted(z.namelist())

    forbidden_prefixes = tuple(bundle_policy.get("forbidden_prefixes") or [])
    required_notice_tokens = tuple(bundle_policy.get("required_notice_basename_tokens") or [])
    allowed_package_prefixes = tuple(bundle_policy.get("allowed_package_prefixes") or [])
    root_modules = set(pyproject["tool"]["setuptools"].get("py-modules") or [])
    dist_info_prefix = f"{project['name'].replace('-', '_')}-{project['version']}.dist-info/"

    forbidden = sorted(name for name in names if name.startswith(forbidden_prefixes))
    unexpected: list[str] = []
    for name in names:
        if name.startswith(allowed_package_prefixes):
            continue
        if bundle_policy.get("allow_project_dist_info") is True and name.startswith(dist_info_prefix):
            continue
        if bundle_policy.get("allow_declared_root_py_modules") is True:
            path = Path(name)
            if len(path.parts) == 1 and path.suffix == ".py" and path.stem in root_modules:
                continue
        unexpected.append(name)

    notice_presence = {
        token: any(token in Path(name).name.upper() for name in names)
        for token in required_notice_tokens
    }
    core_present = any(name.startswith("hpfa/modules/core/") and name.endswith(".py") for name in names)
    registry_present = any("/registry/" in name and name.endswith((".json", ".csv", ".tsv")) for name in names)

    exact_lock_present = (repo / "release/dependency_lock_v1.json").is_file()
    bundle_integrity_pass = (
        core_present
        and registry_present
        and not forbidden
        and not unexpected
        and all(notice_presence.values())
        and not mandatory
        and not missing_policy
        and not undeclared_policy
    )
    release_decision = "PASS" if (
        bundle_integrity_pass
        and exact_lock_present
        and dependency_policy.get("production_release") is True
        and dependency_policy.get("public_index_upload_authorized") is True
        and bundle_policy.get("production_release") is True
    ) else "REVIEW_REQUIRED"

    return {
        "audit_id": "hpfa_release_readiness_audit_v1",
        "wheel": wheel.name,
        "wheel_sha256": sha256_file(wheel),
        "wheel_file_count": len(names),
        "bundle_integrity_status": "PASS" if bundle_integrity_pass else "FAIL",
        "release_decision": release_decision,
        "production_release": False,
        "public_index_upload_authorized": bool(dependency_policy.get("public_index_upload_authorized")),
        "commercial_distribution_authorized": bool(dependency_policy.get("commercial_distribution_authorized")),
        "bundle_policy_id": bundle_policy.get("policy_id"),
        "dependency_policy_id": dependency_policy.get("policy_id"),
        "core_present": core_present,
        "registry_present": registry_present,
        "forbidden_bundle_entries": forbidden,
        "unexpected_bundle_entries": sorted(unexpected),
        "notice_presence": notice_presence,
        "mandatory_runtime_dependencies": mandatory,
        "optional_dependency_manifest": {
            name: {**declared_optional[name], **dict(policy_optional.get(name) or {})}
            for name in sorted(declared_optional)
        },
        "missing_license_policy_entries": missing_policy,
        "orphan_license_policy_entries": undeclared_policy,
        "exact_dependency_lock_present": exact_lock_present,
        "reproducible_dependency_resolution": exact_lock_present,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN"
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--wheel", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    wheel = Path(args.wheel).resolve()
    out = Path(args.out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    report = audit(repo, wheel)
    (out / "hpfa_release_readiness_audit_v1.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["bundle_integrity_status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
