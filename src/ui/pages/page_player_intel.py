"""
RR ScoutIQ — Page 4: Player Intelligence Profile
Granular deep-dive on individual player performance across pressure tiers, phases, and match contexts.
"""

from __future__ import annotations
import streamlit as st

from src.ui.components import plot_player_phase_bars, render_header, render_kpi
from src.ui.data_loader import load_all_players, load_player_profile_details


def render_page_player_intel():
    """Render Player Intelligence Profile page."""
    render_header(
        title="Player <span>Intelligence Profile</span>",
        subtitle="Individual Tactical Evaluation • Multi-Tier Pressure Splits • Uncertainty Diagnostics",
        badge="OBJECTIVE SCOUTING PROFILE",
    )

    c_disc, c_scope = st.columns([1, 1.5])
    with c_disc:
        discipline = st.radio("Primary Discipline", ["Batting", "Bowling"], horizontal=True)
    with c_scope:
        scope = st.radio("Context Scope", ["IPL Primary", "All T20 Supplementary"], horizontal=True)
        scope_key = "ipl" if "IPL" in scope else "all"

    disc_key = "batters" if discipline == "Batting" else "bowlers"
    players_df = load_all_players(discipline=disc_key, scope=scope_key, min_balls=45)

    if players_df.empty:
        st.warning("No players found in this category.")
        return

    player_names = sorted(players_df["player_name"].unique().tolist())
    selected_name = st.selectbox("Select Player to Inspect:", player_names, index=0)

    p_data = players_df[players_df["player_name"] == selected_name].iloc[0]
    splits = load_player_profile_details(selected_name)

    st.markdown("---")

    # Header Card
    style_info = f" • {p_data.get('bowling_style', '')}" if discipline == "Bowling" else ""
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #001C55 0%, #0A192F 100%); padding: 20px 28px; border-radius: 12px; border-left: 6px solid #E6007E; color: white; margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <span style="font-size: 2.0rem; font-weight: 800;">{p_data['player_name']}</span>
                <span style="font-size: 1.0rem; color: #94A3B8; margin-left: 12px;">{p_data['player_role']}{style_info}</span>
            </div>
            <div style="text-align: right;">
                <span style="background: #E6007E; color: white; padding: 4px 14px; border-radius: 16px; font-weight: 800; font-size: 1.1rem;">Rank #{p_data['rank']}</span>
                <div style="font-size: 0.85rem; color: #94A3B8; margin-top: 4px;">Score: <b>{p_data['pressure_score']:.2f}</b> / 100</div>
            </div>
        </div>
        <div style="font-size: 0.85rem; color: #CBD5E1; margin-top: 8px;">
            <b>Teams:</b> {p_data['teams_represented']} | <b>Competitions:</b> {p_data['competitions_played']}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 3-Tier Metric Comparison Row
    st.markdown("### 📊 Performance Across Pressure Tiers")
    c1, c2, c3, c4 = st.columns(4)

    if discipline == "Batting":
        render_kpi(c1, "Career Baseline", f"{p_data['overall_sr']:.1f} SR", subtext=f"{p_data['total_balls_faced']} career balls")
        render_kpi(c2, "High Pressure (P ≥ 50)", f"{p_data['pressure_sr']:.1f} SR", delta=f"{p_data['clutch_sr_delta']:+.1f} Δ", subtext=f"{p_data['pressure_balls_faced']} balls • {p_data['pressure_runs']} runs")
        render_kpi(c3, "Shrunk Posterior SR", f"{p_data['shrunk_pressure_sr']:.1f} SR", subtext=f"90% CI: [{p_data['ci_lower_90_sr']:.1f}, {p_data['ci_upper_90_sr']:.1f}]")
        render_kpi(c4, "Strike Rotation", f"{p_data['pressure_dot_pct']:.1f}% Dot", subtext=f"{p_data['pressure_bnd_pct']:.1f}% Boundary rate")
    else:
        render_kpi(c1, "Career Baseline", f"{p_data['overall_econ']:.2f} Econ", subtext=f"{p_data['total_legal_balls']} career balls")
        render_kpi(c2, "High Pressure (P ≥ 50)", f"{p_data['pressure_econ']:.2f} Econ", delta=f"{p_data['clutch_econ_delta']:+.2f} Δ", subtext=f"{p_data['pressure_legal_balls']} balls • {p_data['pressure_wkts']} wkts")
        render_kpi(c3, "Shrunk Posterior Econ", f"{p_data['shrunk_pressure_econ']:.2f} Econ", subtext=f"90% CI: [{p_data['ci_lower_90_econ']:.2f}, {p_data['ci_upper_90_econ']:.2f}]")
        render_kpi(c4, "Dot Ball Generation", f"{p_data['pressure_dot_pct']:.1f}% Dot", subtext=f"{p_data['pressure_bnd_pct']:.1f}% Boundary conceded")

    st.markdown("---")

    # Phase and Situational Chart
    st.markdown("### 🏟️ Situational Execution & Phase Breakdown")
    col_chart, col_notes = st.columns([1.6, 1])

    with col_chart:
        st.plotly_chart(plot_player_phase_bars(splits, discipline), use_container_width=True)

    with col_notes:
        st.markdown("#### 🎯 Scouting Assessment")
        st.markdown(f"""
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; padding: 16px; border-radius: 8px;">
            <p><b>Observed Strengths:</b><br>{p_data['main_strengths']}</p>
            <p><b>Statistical Caveats:</b><br>{p_data['main_limitations']}</p>
            <p><b>Potential Tactical Fit:</b><br>{p_data['tactical_role_fit']}</p>
            <p style="font-size: 0.8rem; color: #64748B;"><b>External Verification Required:</b><br>{p_data['verification_required']}</p>
        </div>
        """, unsafe_allow_html=True)
