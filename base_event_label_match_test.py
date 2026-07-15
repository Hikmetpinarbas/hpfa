from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa/modules/core/base_event_label_semantic_classifier_lite/src"
sys.path.insert(0, str(SRC))

from base_event_label_semantic_classifier import main


if __name__ == "__main__":
    raise SystemExit(main())
