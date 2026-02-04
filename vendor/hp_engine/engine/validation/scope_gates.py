class HPScopeGate:
    """
    Video Asset Policy'ye göre Claim'leri valide eden kapı.
    """
    def validate_claim_against_video(self, claim, video_asset):
        # 1. Absence Claim Reddi (Hard Rule)
        if claim.type == "absence":
            return "REJECTED", "Absence claims are prohibited with video evidence."

        # 2. Dimension Mismatch Denetimi
        if claim.dimension in video_asset.denied_dimensions:
            return "REJECTED", f"Scope Mismatch: Video context '{video_asset.declared_scope}' prohibits '{claim.dimension}' claims."

        # 3. Confidence Check
        if video_asset.confidence < 0.65:
            return "PENDING", "Low confidence title classification; requires manual tag verification."

        return "APPROVED", "Claim matches video policy context."
