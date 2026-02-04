import pandas as pd

class AureliaCore:
    """Pınarbaşı 6-Faz Modelinin Otonom Faz Tespit Motoru."""
    
    def detect_phase(self, x_coord, event_type, ball_recovery=False, ball_loss=False):
        # 1. Build-up (0-33m) | 2. Progression (33-66m) | 3. Incision/Finishing (66-100m)
        if ball_recovery: return "Attacking Transition"
        if ball_loss: return "Defensive Transition"
        
        if 0 <= x_coord < 33: return "Build-up"
        elif 33 <= x_coord < 66: return "Progression"
        elif 66 <= x_coord <= 100:
            if event_type in ['shot', 'penalty']: return "Finishing"
            return "Incision"
        return "Set-Piece"
