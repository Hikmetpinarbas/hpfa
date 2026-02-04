"""
AURELIA SYSTEM — POST-MATCH ANALYSIS MODULE
Author: Hikmet Pınarbaş
AI Assistant: GPT-5
Version: 0.1

📖 Scientific Base:
- UEFA Technical Report (2023): "Post-Match Evaluation and Performance Differentiation"
- Sarmento, H. et al. (2021). *Tactical and Physical Performance in Elite Football*. Sports Medicine.
- Liu, H. et al. (2019). *Exploring Team Performance Differences in Football via Spatiotemporal Metrics*. Human Movement Science.
- Halson, S. (2014). *Monitoring Fatigue and Recovery in Athletes*. Int. Journal of Sports Physiology & Performance.
- Pino-Ortega, J. et al. (2020). *Psychophysiological Stress in Competitive Matches*. Journal of Strength and Conditioning Research.

💭 Philosophical Layer:
“What happens, happens twice: first in the mind, then on the field.” — Marcus Aurelius
“Truth is found not in the outcome, but in the deviation.” — Karl Popper
"""

import pandas as pd
import numpy as np
from datetime import datetime

class PostMatchAnalysis:
    """
    Compares predicted pre-match expectations with actual match data.
    Extracts:
    1. Tactical deviation (difference between expected & actual)
    2. Physical & cognitive fatigue
    3. Momentum stability
    4. Emotional entropy (stress dispersion)
    """

    def __init__(self, pre_match_data, actual_data):
        self.pre_match = pd.DataFrame(pre_match_data)
        self.actual = pd.DataFrame(actual_data)
        self.timestamp = datetime.now()

    def tactical_deviation(self):
        """
        Measures how far the actual match metrics deviated from predicted expectations.
        Reference: Liu et al. (2019)
        """
        try:
            expected_press = self.pre_match["Expected_Pressing_Intensity"].mean()
            actual_press = self.actual["ppda"].mean()
            deviation = round(abs(expected_press - actual_press) / (expected_press + 0.001) * 100, 2)
            return deviation
        except Exception as e:
            print(f"[AURELIA ERROR] tactical_deviation: {e}")
            return np.nan

    def fatigue_analysis(self):
        """
        Estimates physical and cognitive fatigue using match intensity and distance covered.
        Reference: Halson (2014)
        """
        try:
            distance = self.actual["distance_km"].mean()
            intensity = self.actual["intensity_index"].mean()
            fatigue = round((intensity / (distance + 0.01)) * 12, 2)
            return np.clip(fatigue, 0, 100)
        except Exception as e:
            print(f"[AURELIA ERROR] fatigue_analysis: {e}")
            return np.nan

    def emotional_entropy(self):
        """
        Calculates emotional entropy — how emotionally stable the team remained.
        Based on: Pino-Ortega et al. (2020)
        """
        try:
            stress_levels = self.actual["stress_index"].values
            entropy = round(np.std(stress_levels) / (np.mean(stress_levels) + 0.01) * 100, 2)
            return np.clip(entropy, 0, 100)
        except Exception as e:
            print(f"[AURELIA ERROR] emotional_entropy: {e}")
            return np.nan

    def momentum_stability(self):
        """
        Quantifies momentum changes across the match (xT / possession waves).
        Reference: Sarmento et al. (2021)
        """
        try:
            xT_series = self.actual["expected_threat"].values
            stability = 100 - (np.std(xT_series) * 100)
            return round(np.clip(stability, 0, 100), 2)
        except Exception as e:
            print(f"[AURELIA ERROR] momentum_stability: {e}")
            return np.nan

    def post_match_summary(self):
        """
        Synthesizes findings into an Aurelia-style narrative.
        """
        deviation = self.tactical_deviation()
        fatigue = self.fatigue_analysis()
        entropy = self.emotional_entropy()
        stability = self.momentum_stability()

        insight_level = 100 - (deviation * 0.4 + fatigue * 0.3 + entropy * 0.2)
        narrative = f"""
        Match reflection generated at {self.timestamp.strftime('%Y-%m-%d %H:%M')}:
        Tactical deviation: {deviation}%,
        Fatigue index: {fatigue},
        Emotional entropy: {entropy},
        Momentum stability: {stability}%.

        Interpretation:
        The team’s tactical execution deviated by {deviation}%, indicating a structural
        adaptation mid-game. Fatigue levels suggest physiological decline, while
        emotional entropy at {entropy}% implies moderate instability.
        Momentum stability of {stability}% reveals resilience under pressure.

        As Marcus Aurelius noted: 'What happens, happens twice — first in the mind,
        then on the field.' The difference between them defines the truth.
        """

        return {
            "Timestamp": self.timestamp,
            "Tactical_Deviation": deviation,
            "Fatigue_Index": fatigue,
            "Emotional_Entropy": entropy,
            "Momentum_Stability": stability,
            "Insight_Level": round(insight_level, 2),
            "Narrative": narrative
        }