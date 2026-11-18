"""
RR ScoutIQ — Page 2: Top 10 Batters Under Pressure
Leaderboard with IPL-only primary rankings, supplementary broader T20 view, interactive filters, and CSV export.
"""

from __future__ import annotations
import csv
import io
from typing import Any
import streamlit as st

from src.ui.components import plot_batting_scatter, render_custom_table, render_header
from src.ui.data_loader import load_all_players


def render_page_batters():
    """Render Top Batters Leaderboard page."""
    render_header(
        title="Top 10 Batters <span>Under Pressure</span>",
        subtitle="Audited Multi-Criteria Reliability Scoring • Rajasthan Royals 2027 Auction Target Identification",
        badge="PRIMARY LEADERBOARD: IPL ENVIRONMENT",
    )

    # Controls Row
    c_scope, c_min, c_search = st.columns([1.5, 1.5, 2])
    with c_scope:
        scope = st.radio(
            "Competition Scope",
            ["IPL Only (Primary)", "All T20 Competitions (Supplementary)"],
            index=0,
            horizontal=True,
        )
        scope_key = "ipl" if "IPL" in scope else "all"

    with c_min:
        min_balls = st.slider("Min Pressure Balls Faced", min_value=45, max_value=120, value=60, step=5)

    with c_search:
        search_query = st.text_input("🔍 Search Batter Name", placeholder="e.g. Sanju Samson, Rinku Singh...")

    # Load data
    players = load_all_players(discipline="batters", scope=scope_key, min_balls=min_balls)

    if search_query:
        players = [p for p in players if search_query.lower() in p.get("player_name", "").lower()]

    if not players:
        st.warning("No batters match the selected filter criteria. Try adjusting the minimum pressure balls or search query.")
        return

    # Top 10 Slice
    top10 = players[:10]

    st.markdown(f"### 📋 Leaderboard: Top {len(top10)} Batters ({scope})")

    col_rename = {
        "rank": "Rank",
        "player_name": "Player Name",
        "player_role": "Role",
        "pressure_score": "Score",
        "confidence_tier": "Confidence",
        "pressure_balls_faced": "P-Balls",
        "pressure_runs": "P-Runs",
        "pressure_sr": "P-SR",
        "shrunk_pressure_sr": "Shrunk SR",
        "overall_sr": "Base SR",
        "clutch_sr_delta": "Clutch Δ",
        "pressure_dot_pct": "Dot %",
        "pressure_bnd_pct": "Bnd %",
        "pressure_avg": "Runs/Out",
        "teams_represented": "Teams",
    }

    render_custom_table(top10, col_rename)

    # Download CSV
    if top10:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(top10[0].keys()))
        writer.writeheader()
        writer.writerows(top10)
        csv_bytes = output.getvalue().encode("utf-8")

        st.download_button(
            label="📥 Download Top 10 Batters (CSV)",
            data=csv_bytes,
            file_name=f"rr_scout_iq_top_10_batters_{scope_key}.csv",
            mime="text/csv",
        )

    st.markdown("---")

    # Scatter Visualization
    st.markdown("### 📈 Clutch Elevation vs Pressure Scoring Landscape")
    st.plotly_chart(plot_batting_scatter(players[:25]), use_container_width=True)

    # Player Profile Expander Drill-Down
    st.markdown("### 🔍 Quick Scouting Insight")
    player_names = [p["player_name"] for p in top10]
    selected_player = st.selectbox("Select a batter to inspect scouting evaluation:", player_names)
    if selected_player:
        p_row = next((p for p in top10 if p["player_name"] == selected_player), None)
        if p_row:
            st.markdown(f"""
            <div class="player-card">
                <h4>#{p_row.get('rank', '-')} {p_row['player_name']} ({p_row.get('player_role', 'Batter')}) — Score: {float(p_row.get('pressure_score', 0)):.2f}</h4>
                <p><b>Observed Statistical Strengths:</b> {p_row.get('main_strengths', 'N/A')}</p>
                <p><b>Statistical Caveats / Limitations:</b> {p_row.get('main_limitations', 'N/A')}</p>
                <p><b>Potential Tactical Fit:</b> {p_row.get('tactical_role_fit', 'N/A')}</p>
                <p><b>External Verification Required:</b> {p_row.get('verification_required', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)
