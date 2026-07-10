#!/usr/bin/env bash
set -euo pipefail

python -m py_compile \
  hpfa/modules/core/multi_signal_evidence_fusion_lite/src/multi_signal_evidence_fusion.py

python -m pytest \
  hpfa/modules/core/multi_signal_evidence_fusion_lite/tests \
  -q
