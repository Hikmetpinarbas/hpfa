from __future__ import annotations
from hp_motor.engine.warnings import single_metric_warning
from hp_motor.narrative.causal_guard import guard

def generate_match_report(metrics, popper: dict) -> str:
    lines = []
    lines.append("HP MOTOR | MOD B (Maç Sonu) | Otomatik Çıktı")
    lines.append(
        f"Integrity: {popper['status']} | {popper.get('reason','')}"
    )

    lines.append("\nObservation / Metric Summary:")
    for m in metrics:
        lines.append(f"- {m.name}: {m.value} [{m.status}]")

    warn = single_metric_warning([
        {"status": m.status} for m in metrics
    ])
    if warn:
        lines.append(f"\n{warn}")

    narrative = (
        "\nNarrative (Gri Dil):\n"
        "Çekirdek metriklerin bir kısmı eksik olabilir; "
        "sistem ABSTAIN etmez, DEGRADED konuşur ve eksikleri görünür kılar."
    )

    lines.append(guard(narrative))
    return "\n".join(lines)
