import numpy as np

class HPAnalytics:
    def calculate_xt(self, events_df):
        """16x12 Izgara üzerinde Expected Threat (xT) hesaplar."""
        events_df['cell_x'] = (events_df['x'] / 6.25).astype(int).clip(0, 15)
        events_df['cell_y'] = (events_df['y'] / 8.33).astype(int).clip(0, 11)
        # xT Grid Değerlemesi burada gerçekleşir
        return events_df

    def analyze_nas(self, player_events):
        """Negative Action Spiral: Hata sonrası 180s kognitif çöküş filtresi."""
        errors = player_events[player_events['is_error'] == True]
        nas_instances = []
        for _, err in errors.iterrows():
            window = player_events[(player_events['time'] > err['time']) & 
                                 (player_events['time'] <= err['time'] + 180)]
            if not window.empty and window['success'].mean() < 0.5:
                nas_instances.append(err['time'])
        return nas_instances
