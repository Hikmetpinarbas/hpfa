from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "hpfa_cyclonedx_sbom_v1",
    ROOT / "tools" / "hpfa_cyclonedx_sbom_v1.py",
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def test_sbom_is_cyclonedx_17_and_hash_binds_wheel(tmp_path: Path) -> None:
    wheel = tmp_path / "hpfa-0.1.0-py3-none-any.whl"
    wheel.write_bytes(b"wheel-bytes")
    bom = MOD.build_sbom(ROOT, wheel)

    assert bom["bomFormat"] == "CycloneDX"
    assert bom["specVersion"] == "1.7"
    assert bom["version"] == 1
    component = bom["metadata"]["component"]
    assert component["name"] == "hpfa"
    assert component["version"] == "0.1.0"
    assert component["hashes"] == [
        {"alg": "SHA-256", "content": hashlib.sha256(b"wheel-bytes").hexdigest()}
    ]
    assert bom["dependencies"] == [{"ref": "hpfa:0.1.0", "dependsOn": []}]


def test_sbom_does_not_misrepresent_optional_dependencies_as_bundled(tmp_path: Path) -> None:
    wheel = tmp_path / "hpfa.whl"
    wheel.write_bytes(b"x")
    bom = MOD.build_sbom(ROOT, wheel)
    assert "components" not in bom
    props = {
        row["name"]: row["value"]
        for row in bom["metadata"]["component"]["properties"]
    }
    assert props["hpfa:optional-dependencies-bundled"] == "false"
    assert props["hpfa:production-release"] == "false"
    assert props["hpfa:dependency-lock-status"] == "INCOMPLETE"


def test_sbom_scope_is_distributed_wheel_only(tmp_path: Path) -> None:
    wheel = tmp_path / "hpfa.whl"
    wheel.write_bytes(b"x")
    bom = MOD.build_sbom(ROOT, wheel)
    props = {row["name"]: row["value"] for row in bom["metadata"]["properties"]}
    assert props["hpfa:sbom-scope"] == "distributed-wheel-only"
