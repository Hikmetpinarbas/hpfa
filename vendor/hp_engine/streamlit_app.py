import streamlit as st
import pandas as pd

from engine.master_orchestrator import MasterOrchestrator


st.set_page_config(page_title="HP-Engine v3", layout="wide")

st.title("HP-Engine v3 — Contract-First Pipeline")
st.caption("Raw → ProviderMap → SOT → Registry → Popper Gate → PlotSpec → Narrative")

with st.sidebar:
    st.subheader("Input")
    uploaded = st.file_uploader("Upload SportsBase (or similar) CSV", type=["csv"])
    phase = st.selectbox("Registry phase", ["tactical", "technical", "physical", "psychological"], index=0)

    st.subheader("Context (optional)")
    league = st.text_input("League", value="generic")
    season = st.text_input("Season", value="")
    opponent_tier = st.selectbox("Opponent tier", ["all", "top4", "mid", "bottom6"], index=0)
    venue = st.selectbox("Venue", ["home", "away", "neutral"], index=0)

    run_btn = st.button("Run match", type="primary", use_container_width=True)

if uploaded is None:
    st.info("Upload a CSV to start.")
    st.stop()

df = pd.read_csv(uploaded)

st.write("### Raw input preview")
st.dataframe(df.head(25), use_container_width=True)

if not run_btn:
    st.stop()

ctx = {"league": league, "season": season, "opponent_tier": opponent_tier, "venue": venue}

orch = MasterOrchestrator(registry_root="canon/registry", provider="sportsbase")
result = orch.run(df, phase=phase, context=ctx)

col1, col2 = st.columns([1, 1])

with col1:
    st.write("## SOT Validation Report")
    st.json(result.validation_report)

    st.write("## Narrative (v1)")
    st.code(result.narrative)

with col2:
    st.write("## Claims")
    st.json(result.claims)

    st.write("## PlotSpecs")
    st.json(result.plotspecs)

st.write("## Canonical events preview (post mapping)")
st.dataframe(result.canonical_events_preview, use_container_width=True)