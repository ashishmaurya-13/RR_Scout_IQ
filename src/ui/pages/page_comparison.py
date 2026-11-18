"""
RR ScoutIQ — Page 5: Head-to-Head Comparison
Comparative multi-player evaluation across normalized metrics, baseline deltas, and sample volumes.
"""

from __future__ import annotations
from typing import Any
import streamlit as st

from src.ui.components import plot_comparison_bars, render_custom_table, render_header
from src.ui.data_loader import load_all_players


def render_page_comparison():
    """Render Head-to-Head Comparison page."""
    render_header(
        title="Head-to-Head <span>Talent Comparison</span>",
        subtitle="Side-by-Side Candidate Evaluation • Trade-Off Analysis for Auction Decision Making",
        badge="AUCTION THINK-TANK TOOL",
    )

    c1, c2 = st.columns([1, 1.5])
    with c1:
        discipline = st.radio("Discipline", ["Batting", "Bowling"], horizontal=True)
    with c2:
        scope = st.radio("Scope", ["IPL Primary", "All T20 Supplementary"], horizontal=True)
        scope_key = "ipl" if "IPL" in scope else "all"

    disc_key = "batters" if discipline == "Batting" else "bowlers"
    players = load_all_players(discipline=disc_key, scope=scope_key, min_balls=45)

    if not players:
        st.warning("No players found in this category.")
        return

    player_names = sorted(list(set(p["player_name"] for p in players)))
    default_selection = player_names[:2] if len(player_names) >= 2 else player_names

    selected_players = st.multiselect(
        f"Select 2 to 4 {discipline} Candidates to Compare:",
        options=player_names,
        default=default_selection,
        max_selections=4,
    )

    if len(selected_players) < 2:
        st.info("Please select at least 2 players to perform a comparative evaluation.")
        return

    compare_players = [p for p in players if p["player_name"] in selected_players]

    st.markdown("---")

    # Visual Comparison Bar Chart
    st.markdown("### 📊 Baseline vs Pressure Execution")
    st.plotly_chart(plot_comparison_bars(compare_players, discipline), use_container_width=True)

    # Detailed Comparison Table
    st.markdown("### 📋 Multi-Metric Side-by-Side Comparison")
    if discipline == "Batting":
        col_rename = {
            "player_name": "Player Name",
            "pressure_score": "Score",
            "pressure_balls_faced": "P-Balls",
            "pressure_sr": "P-SR",
            "shrunk_pressure_sr": "Shrunk SR",
            "overall_sr": "Base SR",
            "clutch_sr_delta": "Clutch Δ",
            "pressure_avg": "Runs/Out",
            "pressure_dot_pct": "Dot %",
            "pressure_bnd_pct": "Bnd %",
            "confidence_tier": "Confidence",
        }
    else:
        col_rename = {
            "player_name": "Player Name",
            "bowling_style": "Style",
            "pressure_score": "Score",
            "pressure_legal_balls": "P-Balls",
            "pressure_econ": "P-Econ",
            "shrunk_pressure_econ": "Shrunk Econ",
            "overall_econ": "Base Econ",
            "clutch_econ_delta": "Tightening Δ",
            "pressure_wkts": "P-Wkts",
            "pressure_dot_pct": "Dot %",
            "pressure_bnd_pct": "Bnd %",
            "confidence_tier": "Confidence",
        }

    render_custom_table(compare_players, col_rename)

    # Analytical Comparative Takeaway
    st.markdown("### 💡 Comparative Scouting Summary")
    best_player = max(compare_players, key=lambda x: float(x.get("pressure_score", 0)))
    st.success(f"""
    **Platform Assessment:** **{best_player['player_name']}** leads this candidate cohort with a Pressure Score of **{float(best_player.get('pressure_score', 0)):.2f}** (Confidence: {best_player.get('confidence_tier', 'N/A')}).
    - **Key Differentiator:** {best_player.get('main_strengths', 'N/A')}
    - **Context to Consider:** {best_player.get('main_limitations', 'N/A')}
    """)
