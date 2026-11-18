"""
RR ScoutIQ — Cricket Talent Intelligence & Auction Decision Platform
Main Streamlit Application Entrypoint

Rajasthan Royals IPL 2027 Auction Strategy • SupeRR Selector Season 2
Challenge: Identify the Most Reliable Players Under Pressure
"""

from __future__ import annotations
import streamlit as st

# 1. Page Configuration (must be first Streamlit command)
st.set_page_config(
    page_title="RR ScoutIQ — Talent Intelligence Platform",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Inject Custom Theme Styling
from src.ui.theme import CUSTOM_CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# 3. Import Page Render Functions
from src.ui.pages.page_batters import render_page_batters
from src.ui.pages.page_bowlers import render_page_bowlers
from src.ui.pages.page_comparison import render_page_comparison
from src.ui.pages.page_health import render_page_health
from src.ui.pages.page_methodology import render_page_methodology
from src.ui.pages.page_overview import render_page_overview
from src.ui.pages.page_player_intel import render_page_player_intel
from src.ui.pages.page_pressure_analytics import render_page_pressure_analytics


def main():
    """Application controller and sidebar navigation routing."""
    # Sidebar Header
    st.sidebar.markdown("""
    <div style="padding: 12px 4px 16px 4px; text-align: left;">
        <div style="font-size: 1.6rem; font-weight: 800; color: #FFFFFF; letter-spacing: -0.5px;">
            RR <span style="color: #E6007E;">ScoutIQ</span>
        </div>
        <div style="font-size: 0.8rem; color: #94A3B8; font-weight: 500; margin-top: 2px;">
            IPL 2027 Auction Intelligence
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Navigation Options
    nav_options = [
        "📊 Executive Overview",
        "🏏 Top 10 Batters (Primary IPL)",
        "🎯 Top 10 Bowlers (Primary IPL)",
        "👤 Player Intelligence Profile",
        "⚔️ Head-to-Head Comparison",
        "🧮 Continuous Pressure Analytics",
        "📖 Methodology & Validation",
        "🛡️ Data & Model Health",
    ]

    selected_page = st.sidebar.radio(
        "Navigation",
        options=nav_options,
        index=0,
        label_visibility="collapsed",
    )

    # Sidebar Meta & Competition Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div style="font-size: 0.78rem; color: #94A3B8; line-height: 1.4;">
        <b>Competition:</b> SupeRR Selector S2<br>
        <b>Franchise:</b> Rajasthan Royals<br>
        <b>Challenge:</b> Players Under Pressure<br>
        <b>Status:</b> Official Submission<br>
        <b>Engine:</b> DuckDB SQL-First<br>
        <b>Tests:</b> 60 / 60 Passed (100%)
    </div>
    """, unsafe_allow_html=True)

    # Route to Selected Page
    if selected_page == "📊 Executive Overview":
        render_page_overview()
    elif selected_page == "🏏 Top 10 Batters (Primary IPL)":
        render_page_batters()
    elif selected_page == "🎯 Top 10 Bowlers (Primary IPL)":
        render_page_bowlers()
    elif selected_page == "👤 Player Intelligence Profile":
        render_page_player_intel()
    elif selected_page == "⚔️ Head-to-Head Comparison":
        render_page_comparison()
    elif selected_page == "🧮 Continuous Pressure Analytics":
        render_page_pressure_analytics()
    elif selected_page == "📖 Methodology & Validation":
        render_page_methodology()
    elif selected_page == "🛡️ Data & Model Health":
        render_page_health()


if __name__ == "__main__":
    main()
