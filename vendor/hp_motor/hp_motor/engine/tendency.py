from __future__ import annotations
from hp_motor.metrics.metric_object import MetricObject

def build_tendencies(metrics: list[MetricObject]) -> list[str]:
    out = []
    for m in metrics:
        if m.status == "OK":
            out.append(f"{m.name}: veri mevcut, konuşabilir (hüküm değil, eğilim).")
        elif m.status in ("WEAK", "PROXY"):
            out.append(f"{m.name}: zayıf/proxy okuma; bağlamla sınırlı.")
        else:
            out.append(f"{m.name}: UNKNOWN; veri yok, metrik korunuyor.")
    return out
