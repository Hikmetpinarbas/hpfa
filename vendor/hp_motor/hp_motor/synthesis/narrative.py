from __future__ import annotations
from typing import Any, Dict, List

def build_narrative(report_ctx: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Deterministic narrative generator.
    Inputs: report_ctx = {
      events_summary, metrics_raw, metrics_adjusted, context_flags
    }
    """
    findings: List[str] = []
    reasons: List[str] = []
    evidence: List[str] = []
    actions: List[str] = []
    risks: List[str] = []

    es = report_ctx.get("events_summary", {})
    mr = report_ctx.get("metrics_raw", {})
    ma = report_ctx.get("metrics_adjusted", {})
    flags = report_ctx.get("context_flags", [])

    n_seq = es.get("n_sequences", 0)
    n_pos = es.get("n_possessions", 0)

    # BULGULAR
    if n_seq >= n_pos * 2:
        findings.append("Takım topa sahip olduğunda oyunu sık sekanslara bölüyor.")
    else:
        findings.append("Takım topa sahip olduğunda daha uzun ve kesintisiz sekanslar oynuyor.")

    shot = mr.get("metrics", {}).get("M_SHOT_COUNT", {}).get("value", 0)
    prog = mr.get("metrics", {}).get("M_PROG_PASS_COUNT", {}).get("value", 0)

    if shot > 0:
        findings.append("Hücumlar şutla sonuçlanabiliyor.")
    else:
        findings.append("Hücumlar şut üretmekte zorlanıyor.")

    # NEDENLER
    if prog > 0:
        reasons.append("İlerletici pas sayısı hücum sürekliliğini destekliyor.")
    else:
        reasons.append("İlerletici pas eksikliği hücumların tıkanmasına yol açıyor.")

    if any(f.startswith("missing_soft_column") for f in flags):
        reasons.append("Bazı olay alanları eksik olduğu için analiz çözünürlüğü düşüyor.")

    # KANIT
    evidence.append(f"Toplam sekans sayısı: {n_seq}")
    evidence.append(f"Toplam possession sayısı: {n_pos}")
    evidence.append(f"Şut sayısı: {shot}")
    evidence.append(f"İlerletici pas sayısı: {prog}")

    # AKSİYON
    if prog == 0:
        actions.append("Merkez/yarı alan ilerletme rollerinde risk toleransı artırılmalı.")
    if shot == 0:
        actions.append("Final üçüncü bölgeye girişten sonra daha erken şut opsiyonları denenmeli.")

    # RİSK / VARSAYIM
    if "library:DEGRADED" in flags:
        risks.append("Bazı kütüphane artefaktları eksik; sonuçlar temsili olabilir.")
    if any("missing_soft_column" in f for f in flags):
        risks.append("Eksik event alanları sekans ve tempo yorumlarını sınırlayabilir.")

    return {
        "findings": findings,
        "reasons": reasons,
        "evidence": evidence,
        "actions": actions,
        "risks_assumptions": risks,
    }
