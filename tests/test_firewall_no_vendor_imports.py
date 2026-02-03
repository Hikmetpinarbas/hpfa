import ast
from pathlib import Path

FORBIDDEN_PREFIXES = (
    "vendor.",
    "hp_engine.",
    "hp_motor.",
)

# Canon / Orchestrator tarafında vendor importu istemiyoruz.
SCAN_DIRS = [
    Path("canon"),
    Path("orchestrator"),
]

def _iter_py_files():
    for base in SCAN_DIRS:
        if base.exists():
            yield from base.rglob("*.py")

def _imports_in_file(p: Path):
    tree = ast.parse(p.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                yield n.name
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                yield node.module

def test_no_vendor_imports():
    offenders = []
    for p in _iter_py_files():
        for mod in _imports_in_file(p):
            if mod.startswith(FORBIDDEN_PREFIXES):
                offenders.append((str(p), mod))
    assert not offenders, "Vendor import detected:\n" + "\n".join(f"{f} -> {m}" for f, m in offenders)
