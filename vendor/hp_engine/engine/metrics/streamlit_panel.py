from __future__ import annotations

import streamlit as st
from .api import METRICS, MetricCategory, get_metric, get_summary, search_metrics, get_by_category


def render_metrics_explorer():
    st.subheader("📚 Metrics Encyclopedia (HP Engine)")

    summary = get_summary()
    st.caption(f"Total metrics: {summary.get('total_metrics', len(METRICS))}")

    with st.expander("Category summary", expanded=False):
        st.write({c.value: len(get_by_category(c)) for c in MetricCategory})

    mode = st.radio("Mode", ["Lookup by ID", "Search"], horizontal=True)

    if mode == "Lookup by ID":
        metric_id = st.selectbox("Metric ID", options=sorted(METRICS.keys()))
        m = get_metric(metric_id)
        if not m:
            st.error("Metric not found.")
            return
        _render_metric(m)
    else:
        q = st.text_input("Search (name / alias)", value="")
        if q.strip():
            results = search_metrics(q.strip())
            st.caption(f"Results: {len(results)}")
            if results:
                chosen = st.selectbox("Select a metric", options=[r.metric_id for r in results])
                m = get_metric(chosen)
                if m:
                    _render_metric(m)
            else:
                st.warning("No matches.")


def _render_metric(m):
    st.markdown(f"### {m.metric_id} — {m.full_name}")
    st.write(f"**TR:** {m.turkish_name}")
    st.write(f"**Category:** `{m.category.value}` / **Sub:** `{m.subcategory}`")
    st.write(m.description)

    col1, col2 = st.columns(2)
    with col1:
        st.write("**Unit:**", m.unit)
        st.write("**Range:**", m.range)
    with col2:
        st.write("**Dependencies:**", m.dependencies if m.dependencies else "—")
        st.write("**Aliases:**", m.aliases if m.aliases else "—")

    with st.expander("Formula / Method", expanded=False):
        st.code(m.formula or "—")

    with st.expander("Platforms", expanded=False):
        if m.platforms:
            st.json([{
                "platform": p.platform,
                "field_name": p.field_name,
                "calculation_method": p.calculation_method,
                "notes": p.notes,
            } for p in m.platforms])
        else:
            st.write("—")