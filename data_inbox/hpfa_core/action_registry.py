from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import re

import yaml


class RegistryError(RuntimeError):
    pass


def _norm_token(s: str) -> str:
    """
    Canonical normalization for alias matching:
    - casefold
    - trim
    - collapse whitespace
    - map separators to underscore
    - drop non-word except underscore
    """
    s = (s or "").casefold().strip()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("-", "_").replace(" ", "_").replace("/", "_")
    s = re.sub(r"[^\w_]", "", s, flags=re.UNICODE)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


@dataclass(frozen=True)
class CanonAction:
    canonical_action: str
    possession_effect: str
    allowed_states: List[str]
    fail_closed_default: str
    aliases: List[str]
    qualifiers: Dict[str, List[Any]]


class ActionRegistry:
    """
    Loads YAML registry and provides:
    - alias uniqueness HARD FAIL (zero-drift)
    - resolve(raw_action) -> (canonical_action, qualifiers, status)
    """

    def __init__(self, items: List[CanonAction], alias_map: Dict[str, CanonAction]):
        self.items = items
        self.alias_map = alias_map

    @classmethod
    def from_yaml(cls, path: str) -> "ActionRegistry":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, list):
            raise RegistryError("Registry YAML must be a list of items")

        items: List[CanonAction] = []
        alias_map: Dict[str, CanonAction] = {}
        seen_aliases: Dict[str, str] = {}

        for idx, obj in enumerate(data):
            if not isinstance(obj, dict):
                raise RegistryError(f"Invalid registry item at index {idx}")

            canonical_action = str(obj.get("canonical_action", "")).strip()
            if not canonical_action:
                raise RegistryError(f"Missing canonical_action at index {idx}")

            aliases = obj.get("aliases") or []
            if not isinstance(aliases, list) or not all(isinstance(a, (str, int, float)) for a in aliases):
                raise RegistryError(f"aliases must be a list at canonical_action={canonical_action}")

            possession_effect = str(obj.get("possession_effect", "")).strip().upper()
            allowed_states = obj.get("allowed_states") or []
            fail_closed_default = str(obj.get("fail_closed_default", "UNVALIDATED")).strip().upper()
            qualifiers = obj.get("qualifiers") or {}

            if not isinstance(allowed_states, list):
                raise RegistryError(f"allowed_states must be list at {canonical_action}")
            allowed_states = [str(s).strip().upper() for s in allowed_states]

            if not isinstance(qualifiers, dict):
                raise RegistryError(f"qualifiers must be dict at {canonical_action}")
            q2: Dict[str, List[Any]] = {}
            for k, v in qualifiers.items():
                if not isinstance(v, list):
                    raise RegistryError(f"qualifier '{k}' must be list at {canonical_action}")
                q2[str(k).strip()] = v

            item = CanonAction(
                canonical_action=canonical_action.strip().upper(),
                possession_effect=possession_effect,
                allowed_states=allowed_states,
                fail_closed_default=fail_closed_default,
                aliases=[str(a) for a in aliases],
                qualifiers=q2,
            )
            items.append(item)

            for raw_alias in item.aliases:
                a = _norm_token(str(raw_alias))
                if not a:
                    continue
                if a in seen_aliases:
                    # HARD FAIL: alias used twice across canonical actions
                    prev = seen_aliases[a]
                    raise RegistryError(
                        f"Duplicate alias '{a}' found in both {prev} and {item.canonical_action}"
                    )
                seen_aliases[a] = item.canonical_action
                alias_map[a] = item

        return cls(items=items, alias_map=alias_map)

    def resolve(
        self,
        raw_action: str,
        *,
        hint_gk_holds: Optional[bool] = None,
    ) -> Tuple[str, Dict[str, Any], str]:
        """
        Returns:
        - canonical_action (or 'UNKNOWN')
        - qualifiers dict (may include gk_holds)
        - status: VALID | UNVALIDATED
        """
        key = _norm_token(raw_action)
        if not key or key not in self.alias_map:
            return ("UNKNOWN", {}, "UNVALIDATED")

        item = self.alias_map[key]
        q: Dict[str, Any] = {}

        # GK_SAVE qualifier support
        if item.canonical_action == "GK_SAVE":
            if hint_gk_holds is None:
                # default: if alias suggests parry/punch => holds False
                if key in {"parry", "punch", "yumruklama", "çelme", "sut_cikarma", "şut_çıkarma"}:
                    q["gk_holds"] = False
                else:
                    # conservative: unknown hold => False (prevents false "control")
                    q["gk_holds"] = False
            else:
                q["gk_holds"] = bool(hint_gk_holds)

        return (item.canonical_action, q, "VALID")
