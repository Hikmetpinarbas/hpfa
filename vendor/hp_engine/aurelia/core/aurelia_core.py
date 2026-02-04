class AureliaCore:
    """6-Fazlı Oyun Modeli Tespit ve Karar Motoru."""
    def detect_phase(self, event):
        x = event['x']
        # 1. Build-up (0-33m) | 2. Progression (33-66m) | 3. Incision/Finishing (66-100m)
        if 0 <= x < 33: return "Build-up"
        elif 33 <= x < 66: return "Progression"
        elif 66 <= x <= 100:
            return "Finishing" if event.get('is_box_entry') else "Incision"
        # 4. Transitions (Top kaybı/kazancı anı)
        if event.get('action') in ['interception', 'loss']: return "Transition"
        return "General"
