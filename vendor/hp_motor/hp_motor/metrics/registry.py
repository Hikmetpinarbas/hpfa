from typing import List
from .metric_object import MetricObject

class MetricRegistry:
    def __init__(self) -> None:
        self._items: List[MetricObject] = []

    def add(self, m: MetricObject) -> None:
        # KURAL: Hiçbir metrik silinmez.
        self._items.append(m)

    def all(self) -> List[MetricObject]:
        return list(self._items)
