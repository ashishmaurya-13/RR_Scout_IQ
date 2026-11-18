"""
RR ScoutIQ — Page 6: Continuous Pressure Analytics & Live Match-State Simulator
Deep dive into mathematical formulations, empirical distributions, and interactive pressure calculator.
"""

from __future__ import annotations
import math
import streamlit as st

from src.ui.components import plot_hazard_curve, plot_pressure_histogram, render_header
from src.ui.data_loader import load_pressure_distribution


def calculate_chase_pressure(rrr: float, wickets_lost: int, balls_remaining: int, total_balls: int = 120, runs_required: int = 40) -> tuple[float, dict[str, float]]:
    """Interactive client-side implementation of audited Chase Pressure Index."""
    # 1. Sigmoidal Rate Pressure (R0 = 9.0, kr = 0.22)
    f_rate = 1.0 / (1.0 + math.exp(-0.22 * (rrr - 9.0)))
    
    # 2. Non-linear Resource Scarcity
    wickets_in_hand = max(1, 10 - wickets_lost)
    f_wkt = 1.0 - math.pow(wickets_in_hand / 10.0, 0.75)
    
    # 3. Monotonic Temporal Urgency Horizon (strictly increasing as balls run out)
    elapsed_fraction = 1.0 - (min(balls_remaining, total_balls) / max(1, total_balls))
    f_urgency = 0.20 + 0.80 * math.pow(elapsed_fraction, 1.25)
    
    # 4. Climax Multiplier
    m_close = 1.15 if runs_required <= 25 and balls_remaining <= 18 else 1.00
    
    # Composite CPI
    cpi = min(100.0, max(0.0, 100.0 * (0.55 * f_rate + 0.30 * f_wkt + 0.15 * f_urgency) * m_close))
    
    return round(cpi, 2), {
        "Rate Pressure": round(f_rate, 3),
        "Resource Scarcity": round(f_wkt, 3),
        "Temporal Urgency": round(f_urgency, 3),
        "Climax Multiplier": m_close,
    }


def calculate_inn1_pressure(crr: float, wickets_lost: int, legal_balls_bowled: int, total_balls: int = 120) -> tuple[float, dict[str, float]]:
    """Interactive client-side implementation of First-Innings Structural Pressure."""
    fraction_bowled = min(1.0, legal_balls_bowled / max(1, total_balls))
    expected_wkts = 6.0 * math.pow(fraction_bowled, 0.85)
    excess_wkts = max(0.0, wickets_lost - expected_wkts)
    
    wickets_in_hand = max(1, 10 - wickets_lost)
    s_wkt = min(1.0, (excess_wkts / 3.5) + 0.50 * (1.0 - wickets_in_hand / 10.0))
    
    # Stagnation post-Powerplay
    s_stag = min(1.0, max(0.0, (8.34 - crr) / 3.5)) if legal_balls_bowled >= 36 else 0.0
    
    # Innings Phase Ramp
    if legal_balls_bowled <= 36:
        l_phase = 0.25
    elif legal_balls_bowled <= 90:
        l_phase = 0.40
    else:
        l_phase = 0.70 + 0.30 * ((legal_balls_bowled - 90) / 30.0)
        
    fpi = min(100.0, max(0.0, 100.0 * (0.45 * s_wkt + 0.20 * s_stag + 0.35 * l_phase)))
    
    return round(fpi, 2), {
        "Wicket Stress": round(s_wkt, 3),
        "Stagnation Penalty": round(s_stag, 3),
        "Phase Leverage": round(l_phase, 3),
    }


def render_page_pressure_analytics():
    """Render Continuous Pressure Analytics page with live match-state simulator."""
    render_header(
        title="Continuous <span>Pressure Architecture</span>",
        subtitle="Mathematical Foundations • Pre-Delivery Match-State Modeling • Live Scenario Simulator",
        badge="SCIENTIFIC ENGINE AUDIT",
    )

    pressure_df = load_pressure_distribution()

    st.markdown("### 🧮 Interactive Match-State Pressure Simulator")
    st.write("Adjust the live match variables below to compute the exact, pre-delivery pressure score in real time:")

    sim_innings = st.radio("Select Match State", ["Chasing (2nd Innings Target Pressure)", "Batting First (1st Innings Structural Pressure)"], horizontal=True)

    if "Chasing" in sim_innings:
        c1, c2, c3 = st.columns(3)
        with c1:
            runs_needed = st.number_input("Runs Required to Win", min_value=1, max_value=250, value=48)
            balls_left = st.number_input("Legal Balls Remaining", min_value=1, max_value=120, value=24)
        with c2:
            wickets_down = st.number_input("Wickets Lost", min_value=0, max_value=9, value=4)
            match_len = st.selectbox("Scheduled Match Length", [120, 60], format_func=lambda x: f"{x//6} Overs ({x} balls)")
        with c3:
            rrr = round((runs_needed * 6.0) / max(1, balls_left), 2)
            st.metric("Computed Required Run Rate", f"{rrr:.2f} RPO")

        score, breakdown = calculate_chase_pressure(rrr, wickets_down, balls_left, match_len, runs_needed)

        # Result Banner
        tier_label = "EXTREME HIGH LEVERAGE (CLUTCH)" if score >= 65 else ("HIGH PRESSURE" if score >= 50 else ("MEDIUM PRESSURE" if score >= 30 else "LOW PRESSURE"))
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #001C55 0%, #0A192F 100%); padding: 18px 24px; border-radius: 10px; border-left: 6px solid #E6007E; color: white; margin-top: 10px;">
            <div style="font-size: 0.9rem; text-transform: uppercase; color: #E6007E; font-weight: 700;">Pre-Delivery Chase Pressure Index (CPI)</div>
            <div style="font-size: 2.4rem; font-weight: 800;">{score:.2f} <span style="font-size: 1.1rem; color: #94A3B8;">/ 100.0</span></div>
            <div style="font-size: 0.95rem; color: #E2E8F0; margin-top: 4px;">Classification: <b>{tier_label}</b></div>
            <div style="font-size: 0.85rem; color: #94A3B8; margin-top: 6px;">
                Components: Rate Pressure = {breakdown['Rate Pressure']} | Wicket Scarcity = {breakdown['Resource Scarcity']} | Temporal Urgency = {breakdown['Temporal Urgency']} | Climax Multiplier = {breakdown['Climax Multiplier']}x
            </div>
        </div>
        """, unsafe_allow_html=True)

    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            overs_bowled = st.slider("Completed Overs Bowled", min_value=1, max_value=19, value=14)
            runs_scored = st.number_input("Current Team Runs", min_value=10, max_value=280, value=112)
        with c2:
            wickets_down = st.number_input("Wickets Lost", min_value=0, max_value=9, value=4)
            match_len = st.selectbox("Scheduled Match Length", [120, 60], format_func=lambda x: f"{x//6} Overs ({x} balls)")
        with c3:
            balls_bowled = overs_bowled * 6
            crr = round((runs_scored * 6.0) / max(1, balls_bowled), 2)
            st.metric("Current Run Rate (CRR)", f"{crr:.2f} RPO")

        score, breakdown = calculate_inn1_pressure(crr, wickets_down, balls_bowled, match_len)

        tier_label = "EXTREME HIGH LEVERAGE" if score >= 65 else ("HIGH PRESSURE" if score >= 50 else ("MEDIUM PRESSURE" if score >= 30 else "LOW PRESSURE"))
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #001C55 0%, #0A192F 100%); padding: 18px 24px; border-radius: 10px; border-left: 6px solid #004BA0; color: white; margin-top: 10px;">
            <div style="font-size: 0.9rem; text-transform: uppercase; color: #60A5FA; font-weight: 700;">Pre-Delivery First-Innings Pressure Index (FPI)</div>
            <div style="font-size: 2.4rem; font-weight: 800;">{score:.2f} <span style="font-size: 1.1rem; color: #94A3B8;">/ 100.0</span></div>
            <div style="font-size: 0.95rem; color: #E2E8F0; margin-top: 4px;">Classification: <b>{tier_label}</b></div>
            <div style="font-size: 0.85rem; color: #94A3B8; margin-top: 6px;">
                Components: Wicket Stress = {breakdown['Wicket Stress']} | Stagnation Penalty = {breakdown['Stagnation Penalty']} | Phase Leverage = {breakdown['Phase Leverage']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Empirical Validation Charts
    st.markdown("### 📊 Empirical Delivery Distribution & Behavioral Verification")
    g1, g2 = st.columns(2)
    with g1:
        st.plotly_chart(plot_pressure_histogram(pressure_df), use_container_width=True)
    with g2:
        st.plotly_chart(plot_hazard_curve(pressure_df), use_container_width=True)

    # Reality Check Table
    st.markdown("#### 🔍 Behavior Across Pressure Tiers (200,896 Scored Deliveries)")
    st.dataframe(
        pressure_df.rename(columns={
            "pressure_tier": "Pressure Tier",
            "deliveries": "Deliveries",
            "bat_sr": "Batter SR",
            "bowl_econ": "Bowler Econ",
            "dot_pct": "Dot Ball %",
            "bnd_pct": "Boundary %",
            "wkt_hazard": "Wicket Hazard Rate (%)",
        }),
        use_container_width=True,
        hide_index=True,
    )
