"""
RR ScoutIQ — Page 1: Executive Overview
High-level competition summary, dataset statistics, top pressure performers, and architecture overview.
"""

from __future__ import annotations
import streamlit as st

from src.ui.components import (
    plot_hazard_curve,
    plot_pressure_histogram,
    render_header,
    render_kpi,
)
from src.ui.data_loader import (
    load_db_overview,
    load_leaderboard,
    load_pressure_distribution,
)


def render_page_overview():
    """Render Executive Overview dashboard page."""
    render_header(
        title="RR ScoutIQ <span>Intelligence Platform</span>",
        subtitle="Rajasthan Royals IPL 2027 Auction Strategy • SupeRR Selector Season 2",
        badge="PRIMARY DELIVERABLE: IDENTIFY THE MOST RELIABLE PLAYERS UNDER PRESSURE",
    )

    overview = load_db_overview()
    pressure_df = load_pressure_distribution()
    top_bats = load_leaderboard(discipline="batters", scope="ipl", min_balls=60)
    top_bowls = load_leaderboard(discipline="bowlers", scope="ipl", min_balls=60)

    # Top KPI Row
    st.markdown("### 🏆 Platform Census & Coverage")
    c1, c2, c3, c4, c5 = st.columns(5)
    render_kpi(c1, "IPL Matches Covered", f"{overview['ipl_matches']}", subtext="367 played + 4 abandoned")
    render_kpi(c2, "Total Deliveries", f"{overview['total_deliveries']:,}", subtext="200,896 scored pre-delivery")
    render_kpi(c3, "High-Pressure Balls", f"{overview['hp_deliveries']:,}", subtext="21.2% high leverage (P ≥ 50)")
    render_kpi(c4, "Qualified Batters (IPL)", f"{len(top_bats)}", subtext="Min 60 IPL pressure balls")
    render_kpi(c5, "Qualified Bowlers (IPL)", f"{len(top_bowls)}", subtext="Min 60 IPL pressure balls")

    st.markdown("---")

    # Top Performers Quick View
    st.markdown("### ⚡ Top IPL Pressure Performers (Primary Auction Intelligence)")
    col_bat, col_bowl = st.columns(2)

    with col_bat:
        st.markdown("#### 🏏 Top 3 IPL Batters Under Pressure")
        for i, b in top_bats.head(3).iterrows():
            st.markdown(f"""
            <div style="background: #F8FAFC; border-left: 4px solid #E6007E; padding: 12px 16px; border-radius: 8px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 1.1rem; font-weight: 700; color: #001C55;">#{i+1} {b['player_name']}</span>
                    <span style="background: #E6007E; color: white; padding: 2px 8px; border-radius: 12px; font-weight: 700; font-size: 0.85rem;">Score: {b['pressure_score']:.2f}</span>
                </div>
                <div style="font-size: 0.85rem; color: #475569; margin-top: 4px;">
                    <b>{b['pressure_balls_faced']}</b> balls • <b>{b['pressure_runs']}</b> runs • <b>{b['pressure_sr']:.1f}</b> SR • <span style="color: #059669; font-weight: 600;">+{b['clutch_sr_delta']:.1f} Clutch Δ</span>
                </div>
                <div style="font-size: 0.78rem; color: #64748B; margin-top: 2px;">{b['teams_represented']}</div>
            </div>
            """, unsafe_allow_html=True)

    with col_bowl:
        st.markdown("#### 🎯 Top 3 IPL Bowlers Under Pressure")
        for i, b in top_bowls.head(3).iterrows():
            st.markdown(f"""
            <div style="background: #F8FAFC; border-left: 4px solid #001C55; padding: 12px 16px; border-radius: 8px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 1.1rem; font-weight: 700; color: #001C55;">#{i+1} {b['player_name']}</span>
                    <span style="background: #001C55; color: white; padding: 2px 8px; border-radius: 12px; font-weight: 700; font-size: 0.85rem;">Score: {b['pressure_score']:.2f}</span>
                </div>
                <div style="font-size: 0.85rem; color: #475569; margin-top: 4px;">
                    <b>{b['pressure_legal_balls']}</b> balls • <b>{b['pressure_wkts']}</b> wkts • <b>{b['pressure_econ']:.2f}</b> Econ • <span style="color: #059669; font-weight: 600;">+{b['clutch_econ_delta']:.2f} Tightening Δ</span>
                </div>
                <div style="font-size: 0.78rem; color: #64748B; margin-top: 2px;">{b['teams_represented']}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # Analytical Foundation & Visualizations
    st.markdown("### 📊 Continuous Pressure Architecture & Empirical Validation")
    g1, g2 = st.columns(2)
    with g1:
        st.plotly_chart(plot_pressure_histogram(pressure_df), use_container_width=True)
    with g2:
        st.plotly_chart(plot_hazard_curve(pressure_df), use_container_width=True)

    # Explanatory Notes Callout
    st.info("""
    **Analytical Principles & Scope Disclosures:**
    - **Primary Leaderboard:** Exclusively evaluates IPL matches (371 fixtures, 2022–2026), providing direct auction relevance without synthetic cross-competition multipliers.
    - **Zero Future Leakage:** Pressure is reconstructed strictly prior to delivery release using cumulative match state (`ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING`).
    - **Bayesian Reliability:** Small-sample noise is regressed toward league priors using Empirical Bayes shrinkage ($n_0 = 45.0$ deliveries) with 90% credible intervals.
    """)
