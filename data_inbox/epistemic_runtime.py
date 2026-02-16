from enum import Enum
from typing import Dict, Optional

class EpistemicStatus(str, Enum):
    VALID = "VALID"
    UNVALIDATED = "UNVALIDATED"
    FALSIFIED = "FALSIFIED"
    INCONCLUSIVE = "INCONCLUSIVE"

class ClaimType(str, Enum):
    OBSERVATION = "OBSERVATION"
    INTERPRETATION = "INTERPRETATION"
    MODEL = "MODEL"

def evaluate_epistemic_status(
    claim_type: ClaimType,
    validation_flags: Dict[str, Optional[bool]],
    popper_test_passed: Optional[bool] = None
) -> EpistemicStatus:

    # Fail-closed: identity is mandatory for everything
    if not validation_flags.get("identity", False):
        return EpistemicStatus.UNVALIDATED

    if claim_type == ClaimType.OBSERVATION:
        if validation_flags.get("anomaly", False):
            return EpistemicStatus.INCONCLUSIVE
        return EpistemicStatus.VALID

    if claim_type == ClaimType.INTERPRETATION:
        if not validation_flags.get("context", False):
            return EpistemicStatus.INCONCLUSIVE
        if validation_flags.get("anomaly", False):
            return EpistemicStatus.INCONCLUSIVE
        return EpistemicStatus.VALID

    if claim_type == ClaimType.MODEL:
        if not validation_flags.get("context", False):
            return EpistemicStatus.INCONCLUSIVE
        if not validation_flags.get("intent", False):
            return EpistemicStatus.INCONCLUSIVE
        if validation_flags.get("cognitive") is False:
            return EpistemicStatus.INCONCLUSIVE
        if popper_test_passed is False:
            return EpistemicStatus.FALSIFIED
        if validation_flags.get("anomaly", False):
            return EpistemicStatus.INCONCLUSIVE
        return EpistemicStatus.VALID

    return EpistemicStatus.UNVALIDATED


if __name__ == "__main__":
    flags = {
        "identity": True,
        "context": True,
        "intent": True,
        "cognitive": None,
        "anomaly": False
    }

    status = evaluate_epistemic_status(
        ClaimType.MODEL,
        flags,
        popper_test_passed=True
    )

    print(status)
