#!/usr/bin/env python3
"""
Canon Hash Gate (Fail-Closed)

- Reads: canon/canon_hashes.json
- Verifies every listed file exists and matches sha256.
Exit codes:
  0 = PASS
  1 = FAIL (mismatch / missing)
  2 = FAIL_CLOSED (runtime / malformed manifest)
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict


MANIFEST = Path("canon/canon_hashes.json")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fail(msg: str, code: int) -> int:
    print(msg)
    return code


def main() -> int:
    try:
        if not MANIFEST.exists():
            return fail(f"FAIL missing manifest: {MANIFEST}", 1)

        d = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if not isinstance(d, dict):
            return fail("FAIL_CLOSED manifest root not dict", 2)

        algo = d.get("algo")
        if algo != "sha256":
            return fail(f"FAIL_CLOSED unsupported algo: {algo}", 2)

        files = d.get("files")
        if not isinstance(files, dict) or not files:
            return fail("FAIL_CLOSED manifest.files missing/empty", 2)

        any_fail = False
        print("== CANON HASH GATE ==")
        for rel, expected in files.items():
            if not isinstance(rel, str) or not rel.strip():
                any_fail = True
                print("FAIL invalid path key in manifest")
                continue
            if not isinstance(expected, str) or len(expected.strip()) < 32:
                any_fail = True
                print(f"FAIL invalid hash for {rel}")
                continue

            p = Path(rel)
            if not p.exists():
                any_fail = True
                print(f"FAIL missing file: {rel}")
                continue

            actual = sha256_file(p)
            if actual != expected.strip():
                any_fail = True
                print(f"FAIL hash mismatch: {rel}")
                print(f"  expected: {expected.strip()}")
                print(f"  actual  : {actual}")
            else:
                print(f"PASS {rel}")

        return 1 if any_fail else 0

    except Exception as e:
        print(f"FAIL_CLOSED runtime_error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
