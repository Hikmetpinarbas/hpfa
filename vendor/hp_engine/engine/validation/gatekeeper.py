class HPGatekeeper:
    """
    Status Gates & Evidence Hierarchy Denetleyicisi.
    'No-evidence, no-prediction' kuralını burada enforce eder.
    """
    
    def check_confirmed_gate(self, claim: Dict):
        """
        Confirmed Gate: 
        1. RAW kanıt zorunluluğu (primary_raw).
        2. Maksimum belirsizlik (Uncertainty) eşiği denetimi.
        """
        uncertainty = claim.get("uncertainty", {}).get("level", 3)
        has_primary = any(e["evidence_type"] == "primary_raw" for e in claim.get("evidence", []))
        
        # Confirmed: RAW şart, Uncertainty <= 1 (Pattern Contract v1)
        if has_primary and uncertainty <= 1:
            return "confirmed"
        return "candidate"

    def check_published_gate(self, claim: Dict):
        """
        Published Gate: Atıfsız (Citation) hüküm yayınlanamaz.
        'Published' raporuna çıkışta gate eder.
        """
        citations = claim.get("citations", [])
        if not citations:
            return False, "UYARI: Atıfsız hüküm mühürlenemez (Draft statüsünde kaldı)."
        return True, "Mühürlendi: Kaynaklar doğrulandı."
