from engine.hp_engine_logic import HPLogic
from engine.hp_engine_analytics import HPAnalytics
from engine.hp_engine_vision import HPVision

class HPManager:
    """7 Ana ve 3 Yardımcı Modülü koordine eden Master Orchestrator."""
    
    def run_hybrid_analysis(self, files, videos, mode, helpers):
        # 1. Veri Okuma
        from engine.hp_engine_reader import HPReader
        reader = HPReader()
        store = reader.ingest(files)
        
        logic = HPLogic()
        analytics = HPAnalytics()
        vision = HPVision()
        
        # 2. Ana Analiz Seçimi (7 Modül)
        analysis_map = {
            "Pre-Match Analysis": logic.run_pre_match_analysis,
            "Post-Match Analysis": logic.run_post_match_analysis,
            "Individual Analysis": logic.run_individual_analysis,
            "Team Tactical Analysis": logic.run_team_tactical_analysis,
            "Seasonal & Tournament Analysis": logic.run_seasonal_tournament_analysis,
            "Team Squad Engineering Analysis": logic.run_team_squad_engineering_analysis,
            "General Analysis": logic.run_general_analysis
        }
        
        main_result = analysis_map.get(mode, logic.run_general_analysis)(store)
        
        # 3. Yardımcı Modüller (3 Modül - Seçmeli)
        helper_results = {}
        if helpers.get("video") and videos:
            helper_results["video"] = vision.video_analysis_analysis(videos)
        if helpers.get("body"):
            helper_results["body"] = vision.body_position_orientation_rotation_analysis(store)
        if helpers.get("positional"):
            helper_results["positional"] = vision.positional_analysis_analysis(store)
            
        return {
            "main": main_result,
            "helpers": helper_results,
            "metadata": {"team": "Analiz Edilen Birim", "mode": mode}
        }
