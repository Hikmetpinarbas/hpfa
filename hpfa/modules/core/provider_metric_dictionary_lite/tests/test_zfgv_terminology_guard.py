from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]

TEXT_SUFFIXES = {
    ".py", ".json", ".md", ".txt", ".tsv", ".csv", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".sh", ".ps1", ".xml", ".html", ".js", ".ts",
}
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
FORBIDDEN = tuple(part.casefold() for part in (
    "event" + "_only",
    "event" + "-only",
    "event" + " only",
))


class ZFGVTerminologyGuardTests(unittest.TestCase):
    def test_repository_uses_zfgv_as_observation_language(self):
        hits: list[str] = []
        for path in ROOT.rglob("*"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            rel = path.relative_to(ROOT).as_posix()
            folded_rel = rel.casefold()
            if any(token in folded_rel for token in FORBIDDEN):
                hits.append(f"path:{rel}")
            if not path.is_file() or path.suffix.casefold() not in TEXT_SUFFIXES:
                continue
            try:
                text = path.read_text(encoding="utf-8").casefold()
            except (UnicodeDecodeError, OSError):
                continue
            if any(token in text for token in FORBIDDEN):
                hits.append(f"content:{rel}")
        self.assertEqual(hits, [], "ZFGV terminology guard found retired observation-language remnants:\n" + "\n".join(hits))


if __name__ == "__main__":
    unittest.main()
