class HPTaxonomy:
    """
    HP Engine: 8 Ana Dünya Futbol Sistemi ve Algoritmik Eşikler.
    Akademik Referans: Futbol Zeka Sistemi 1 & 2.
    """
    SYSTEMS = {
        "SYS-001": {
            "name": "Positional Play (Juego de Posición)",
            "thresholds": {"possession": 65, "pass_completion": 0.88, "field_tilt": 65, "ppda": 12.0},
            "critical_roles": ["DM_ANCHOR", "CB_BALL_PLAYING", "ST_FALSE_NINE"]
        },
        "SYS-002": {
            "name": "Gegenpressing (Heavy Metal Football)",
            "thresholds": {"ppda": 8.5, "high_regains": 12, "verticality": 0.70, "sprint_vol": 95},
            "critical_roles": ["ST_PRESSING", "CB_PACE_DEFENDER", "DM_BALL_WINNER"]
        },
        "SYS-003": {
            "name": "Relational Play (Jogo Bonito 2.0)",
            "thresholds": {"pass_combination": 8, "short_pass_ratio": 0.85, "cluster_density": 0.75},
            "critical_roles": ["DM_REGISTA", "ST_PIVOT", "CM_MEZZALA"]
        },
        "SYS-004": {"name": "Vertical Transition", "thresholds": {"vertical_passes": 35, "sprint_distance": 1200}},
        "SYS-005": {"name": "Catenaccio Moderno", "thresholds": {"block_height": 35, "compactness": 450}},
        "SYS-006": {"name": "Total Football 2.0", "thresholds": {"gk_build_up": 25, "baiting_press": 0.8}},
        "SYS-007": {"name": "Direct Verticality", "thresholds": {"direct_speed": 2.5, "long_ball_ratio": 0.18}},
        "SYS-008": {"name": "Asymmetric Attack", "thresholds": {"wingback_xG": 0.25, "man_marking_intensity": 0.9}}
    }

    def validate_system_fit(self, metrics, sys_id):
        target = self.SYSTEM_DATABASE.get(sys_id, {})
        return {m: metrics.get(m, 0) >= v for m, v in target.get("thresholds", {}).items()}
