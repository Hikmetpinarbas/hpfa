from __future__ import annotations

def single_metric_warning(metrics: list[dict]) -> str | None:
    informative = [m for m in metrics if m.get("status") in ("OK", "PROXY")]
    if len(informative) <= 1:
        return (
            "Uyarı (Kahneman): Analiz tek bilgi kanalına dayanmaktadır. "
            "Bu nedenle çıkarımlar temkinle ele alınmalıdır."
        )
    return None
