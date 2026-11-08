"""
RR ScoutIQ — Application Entry Point
Cricket Talent Intelligence & Auction Decision Platform
SupeRR Selector Season 2 — Rajasthan Royals IPL 2027 Auction Strategy
"""

import streamlit as st
from config.settings import (
    PROJECT_NAME,
    FULL_NAME,
    COMPETITION,
    DEADLINE,
    APP_VERSION,
    ENVIRONMENT,
)

# Page configuration
st.set_page_config(
    page_title=f"{PROJECT_NAME} | Talent Intelligence",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Professional cricket analytics styling (Rajasthan Royals themed accents)
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.25rem;
        font-weight: 700;
        color: #0c2340;
        margin-bottom: 0.25rem;
    }
    .sub-header {
        font-size: 1.15rem;
        color: #4a5568;
        font-weight: 500;
        margin-bottom: 1.25rem;
    }
    .badge-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
        margin-bottom: 1.5rem;
    }
    .badge-item {
        background-color: #f0f4f8;
        border-left: 3px solid #d91c5c;
        padding: 0.4rem 0.8rem;
        border-radius: 4px;
        font-size: 0.85rem;
        color: #1a202c;
    }
    .status-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1.25rem;
        margin-bottom: 1.5rem;
    }
    .module-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 1.2rem;
        height: 100%;
        transition: transform 0.15s ease-in-out;
    }
    .module-title {
        font-size: 1.05rem;
        font-weight: 600;
        color: #0c2340;
        margin-bottom: 0.5rem;
    }
    .module-desc {
        font-size: 0.875rem;
        color: #64748b;
        line-height: 1.4;
    }
    .footer {
        margin-top: 3rem;
        padding-top: 1rem;
        border-top: 1px solid #e2e8f0;
        font-size: 0.8rem;
        color: #94a3b8;
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header Section
st.markdown(f'<div class="main-header">🏏 {PROJECT_NAME}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-header">{FULL_NAME}</div>', unsafe_allow_html=True)

# Project Metadata Badges
st.markdown(
    f"""
    <div class="badge-bar">
        <div class="badge-item"><strong>Competition:</strong> {COMPETITION}</div>
        <div class="badge-item"><strong>Deadline:</strong> {DEADLINE}</div>
        <div class="badge-item"><strong>Version:</strong> v{APP_VERSION}</div>
        <div class="badge-item"><strong>Environment:</strong> {ENVIRONMENT.title()}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Project Status Banner
with st.container():
    st.markdown(
        """
        <div class="status-card">
            <h4 style="margin: 0 0 0.5rem 0; color: #0c2340;">Platform Status: Environment Initialized</h4>
            <p style="margin: 0; color: #475569; font-size: 0.925rem;">
                The platform foundation, directory structure, configurations, and dependency suite have been successfully established.
                Analytical pipelines, data ingestion workflows, statistical models, and player scouting interfaces are currently under active development.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Sidebar Navigation (Placeholder for analytical workflows)
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/en/thumb/6/60/Rajasthan_Royals_Logo.svg/300px-Rajasthan_Royals_Logo.svg.png", width=90)
    st.markdown("### Navigation")
    selected_view = st.radio(
        "Platform Modules",
        options=[
            "Overview & Architecture",
            "Data Ingestion & Integrity",
            "Player Performance Analytics",
            "Role Fit & Evaluation",
            "Auction Valuation & Strategy",
            "Scouting Reports",
        ],
        index=0,
    )
    st.divider()
    st.markdown("**Auction Roadmap:** IPL 2027 Strategy")
    st.caption(f"Target Submission: {DEADLINE}")

# Main Content Area: Module Placeholders
st.markdown("### Planned Analytical Modules")
st.caption("Architecture ready for modular implementation across the scouting lifecycle.")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        """
        <div class="module-card">
            <div class="module-title">1. Ingestion & Quality Control</div>
            <div class="module-desc">
                Automated ingestion pipelines for ball-by-ball feeds, match summaries, and tournament registries with schema validation and anomaly checks.
            </div>
            <div style="margin-top: 0.75rem;"><span style="background-color: #f1f5f9; color: #475569; font-size: 0.75rem; padding: 2px 6px; border-radius: 4px;">Status: Foundation Ready</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    st.markdown(
        """
        <div class="module-card">
            <div class="module-title">4. Talent Evaluation & Fit</div>
            <div class="module-desc">
                Multidimensional scoring vectors assessing role execution (Powerplay, Middle Overs, Death), tactical adaptability, and squad composition balance.
            </div>
            <div style="margin-top: 0.75rem;"><span style="background-color: #f1f5f9; color: #475569; font-size: 0.75rem; padding: 2px 6px; border-radius: 4px;">Status: Planned</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        """
        <div class="module-card">
            <div class="module-title">2. Contextual Preprocessing</div>
            <div class="module-desc">
                Phase-of-play categorization, venue boundary adjustments, pitch profile indexing, and opposition quality weighting.
            </div>
            <div style="margin-top: 0.75rem;"><span style="background-color: #f1f5f9; color: #475569; font-size: 0.75rem; padding: 2px 6px; border-radius: 4px;">Status: Planned</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    st.markdown(
        """
        <div class="module-card">
            <div class="module-title">5. Auction Decision Engine</div>
            <div class="module-desc">
                Statistical price forecasting, replacement-level baseline comparisons, budget optimization under purse constraints, and bid simulations.
            </div>
            <div style="margin-top: 0.75rem;"><span style="background-color: #f1f5f9; color: #475569; font-size: 0.75rem; padding: 2px 6px; border-radius: 4px;">Status: Planned</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        """
        <div class="module-card">
            <div class="module-title">3. Statistical & ML Analytics</div>
            <div class="module-desc">
                Expected runs/wickets added (xR / xW), leverage index ratings, survival curve modeling, and domestic performance translation indices.
            </div>
            <div style="margin-top: 0.75rem;"><span style="background-color: #f1f5f9; color: #475569; font-size: 0.75rem; padding: 2px 6px; border-radius: 4px;">Status: Planned</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    st.markdown(
        """
        <div class="module-card">
            <div class="module-title">6. War-Room Dossiers & Exports</div>
            <div class="module-desc">
                Executive briefing generation, automated PDF scout reports, Excel valuation matrices, and interactive player comparison sheets.
            </div>
            <div style="margin-top: 0.75rem;"><span style="background-color: #f1f5f9; color: #475569; font-size: 0.75rem; padding: 2px 6px; border-radius: 4px;">Status: Planned</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Footer
st.markdown(
    f'<div class="footer">RR ScoutIQ &bull; {FULL_NAME} &bull; SupeRR Selector Season 2</div>',
    unsafe_allow_html=True,
)
