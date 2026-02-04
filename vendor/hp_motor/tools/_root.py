from pathlib import Path
import os
import sys

def repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in [p.parent, *p.parents]:
        if (parent / "tools").exists() and (parent / "artifacts").exists():
            return parent
    raise RuntimeError("HP MOTOR ROOT NOT FOUND")

ROOT = repo_root()
os.chdir(ROOT)

# expose for imports
__all__ = ["ROOT"]
