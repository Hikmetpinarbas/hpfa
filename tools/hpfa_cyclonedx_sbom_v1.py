from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_sbom(repo: Path, wheel: Path) -> dict:
    project = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    bundle_policy = json.loads(
        (repo / "release/release_bundle_policy_v1.json").read_text(encoding="utf-8")
    )
    dependency_policy = json.loads(
        (repo / "release/release_dependency_policy_v1.json").read_text(encoding="utf-8")
    )
    lock = json.loads((repo / "release/dependency_lock_v1.json").read_text(encoding="utf-8"))

    name = str(project["name"])
    version = str(project["version"])
    root_ref = f"{name}:{version}"

    return {
        "$schema": "https://cyclonedx.org/schema/bom-1.7.schema.json",
        "bomFormat": "CycloneDX",
        "specVersion": "1.7",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "bom-ref": root_ref,
                "name": name,
                "version": version,
                "hashes": [{"alg": "SHA-256", "content": sha256_file(wheel)}],
                "licenses": [{"license": {"name": "Proprietary"}}],
                "properties": [
                    {"name": "hpfa:distribution:private", "value": "true"},
                    {
                        "name": "hpfa:production-release",
                        "value": str(bool(bundle_policy.get("production_release"))).lower(),
                    },
                    {
                        "name": "hpfa:dependency-lock-status",
                        "value": str(lock.get("lock_status", "MISSING")),
                    },
                    {
                        "name": "hpfa:optional-dependencies-bundled",
                        "value": "false",
                    },
                    {
                        "name": "hpfa:commercial-distribution-authorized",
                        "value": str(
                            bool(dependency_policy.get("commercial_distribution_authorized"))
                        ).lower(),
                    },
                ],
            },
            "properties": [
                {"name": "hpfa:sbom-scope", "value": "distributed-wheel-only"},
                {
                    "name": "hpfa:optional-dependency-policy-id",
                    "value": str(dependency_policy.get("policy_id")),
                },
                {
                    "name": "hpfa:release-bundle-policy-id",
                    "value": str(bundle_policy.get("policy_id")),
                },
            ],
        },
        "dependencies": [{"ref": root_ref, "dependsOn": []}],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--wheel", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    wheel = Path(args.wheel).resolve()
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = build_sbom(repo, wheel)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
