from dataclasses import dataclass
from typing import List, Dict

@dataclass
class PlayerProfile:
    id: str
    name: str
    vulnerabilities: List[str]
    counter_weights: List[str] # Zafiyeti kapatan profil ID'leri

PLAYER_PROFILES = {
    "GK_SWEEPER": PlayerProfile(
        "GK_SWEEPER", "Sweeper-Keeper", 
        ["1v1 shot-stopping", "High line exposure"], 
        ["CB_PACE_DEFENDER", "DM_ANCHOR"]
    ),
    "CB_BALL_PLAYING": PlayerProfile(
        "CB_BALL_PLAYING", "Ball-Playing CB",
        ["Physical duels", "Aerial dominance"],
        ["CB_PHYSICAL_LEADER", "DM_BALL_WINNER"]
    ),
    "ST_FALSE_NINE": PlayerProfile(
        "ST_FALSE_NINE", "False 9",
        ["Goal volume", "Physical presence"],
        ["W_INSIDE_FORWARD", "CM_BOX_TO_BOX"]
    )
}

class HPSquadEngineering:
    def check_counter_weight(self, squad_dict):
        """Kadroda eksik olan 'Karşı Ağırlık' profillerini raporlar."""
        alerts = []
        for pos, profile_id in squad_dict.items():
            profile = PLAYER_PROFILES.get(profile_id)
            if profile:
                for cw in profile.counter_weights:
                    if cw not in squad_dict.values():
                        alerts.append(f"UYARI: {profile.name} zafiyeti için {cw} profili eksik.")
        return alerts
