#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "reporting" / "reasoning_grammar_spine_lite" / "src"
sys.path.insert(0, str(SRC))

from reasoning_grammar_spine import write_outputs

parser = argparse.ArgumentParser()
parser.add_argument("--out-dir", required=True)
args = parser.parse_args()
result = write_outputs(args.out_dir, root=ROOT)
print(json.dumps({"status": result.get("status"), "stage": result.get("stage"), "candidate_count": result.get("candidate_count"), "outputs": result.get("outputs")}, ensure_ascii=False, sort_keys=True))
