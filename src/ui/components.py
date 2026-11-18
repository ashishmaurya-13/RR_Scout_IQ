"""
RR ScoutIQ — Reusable UI Components & Plotly Chart Builders
"""

from __future__ import annotations
from typing import Any
import plotly.graph_objects as go
import streamlit as st

from src.ui.theme import RR_BLUE, RR_GOLD, RR_GREEN, RR_NAVY, RR_PINK, RR_TEXT_MUTED


def render_header(title: str, subtitle: str, badge: str = "OFFICIAL COMPETITION SUBMISSION") -> None:
    """Render the high-impact Rajasthan Royals branded header."""
    html = f"""
    <div class="rr-header-container">
        <div class="rr-header-title">{title}</div>
        <div class="rr-header-subtitle">{subtitle}</div>
        <div class="rr-header-badge">{badge}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_kpi(col, label: str, value: str, delta: str | None = None, subtext: str | None = None, is_pos: bool = True):
    """Render styled KPI card inside a Streamlit column."""
    delta_html = ""
    if delta:
        delta_class = "kpi-delta-pos" if is_pos else "kpi-delta-neg"
        delta_html = f'<span class="{delta_class}">{delta}</span> '

    subtext_html = ""
    if subtext or delta_html:
        subtext_html = f'<div class="kpi-subtext">{delta_html}{subtext or ""}</div>'

    html = f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {subtext_html}
    </div>
    """
    col.markdown(html, unsafe_allow_html=True)


def get_confidence_badge_html(tier: str) -> str:
    """Return colored pill badge for confidence tier."""
    if tier == "High Confidence":
        return '<span class="badge-high">High (λ ≥ 0.70)</span>'
    elif tier == "Moderate Confidence":
        return '<span class="badge-moderate">Moderate (0.50 ≤ λ < 0.70)</span>'
    else:
        return '<span class="badge-low">Low (λ < 0.50)</span>'


def render_custom_table(records: list[dict[str, Any]], column_map: dict[str, str]) -> None:
    """Render an elegant, responsive HTML table matching Rajasthan Royals branding."""
    if not records:
        st.info("No records to display.")
        return

    headers = [column_map.get(k, k) for k in column_map.keys()]
    th_html = "".join(f"<th>{h}</th>" for h in headers)

    tr_html = []
    for r in records:
        tds = []
        for col in column_map.keys():
            val = r.get(col, "")
            if col == "confidence_tier":
                val = get_confidence_badge_html(str(val))
            elif isinstance(val, float):
                val = f"{val:.2f}"
            elif isinstance(val, int) and col != "rank":
                val = f"{val:,}"
            tds.append(f"<td>{val}</td>")
        tr_html.append(f"<tr>{''.join(tds)}</tr>")

    html = f"""
    <div style="overflow-x:auto;">
        <table class="rr-table">
            <thead><tr>{th_html}</tr></thead>
            <tbody>{''.join(tr_html)}</tbody>
        </table>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def plot_pressure_histogram(records: list[dict[str, Any]]) -> go.Figure:
    """Plot distribution of deliveries across pressure tiers."""
    colors = [RR_BLUE, "#0D9488", RR_GOLD, RR_PINK]
    tiers = [r["pressure_tier"] for r in records]
    counts = [r["deliveries"] for r in records]
    fig = go.Figure(data=[
        go.Bar(
            x=tiers,
            y=counts,
            marker_color=colors,
            text=[f"{c:,}" for c in counts],
            textposition="auto",
        )
    ])
    fig.update_layout(
        title="Delivery Population Across Pre-Delivery Pressure Tiers",
        xaxis_title="Pressure Tier",
        yaxis_title="Total Deliveries Bowled",
        template="plotly_white",
        height=320,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def plot_hazard_curve(records: list[dict[str, Any]]) -> go.Figure:
    """Plot wicket hazard rate escalation across pressure tiers."""
    tiers = [r["pressure_tier"] for r in records]
    hazards = [r["wkt_hazard"] for r in records]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=tiers,
        y=hazards,
        mode="lines+markers+text",
        name="Wicket Hazard Rate (%)",
        text=[f"{h:.2f}%" for h in hazards],
        textposition="top center",
        line=dict(color=RR_PINK, width=3),
        marker=dict(size=10, color=RR_NAVY),
    ))
    fig.update_layout(
        title="Wicket Hazard Escalation: Probability of Dismissal Under Pressure",
        xaxis_title="Pressure Tier",
        yaxis_title="Wicket Hazard Rate (%)",
        template="plotly_white",
        height=320,
        margin=dict(l=20, r=20, t=40, b=20),
        yaxis=dict(range=[3.0, 10.0]),
    )
    return fig


def plot_batting_scatter(records: list[dict[str, Any]]) -> go.Figure:
    """Plot Batter Pressure Strike Rate vs Pressure Score with sample size bubbles."""
    x = [r.get("pressure_sr", 0.0) for r in records]
    y = [r.get("pressure_score", 0.0) for r in records]
    sizes = [max(8, min(30, int(r.get("pressure_balls_faced", 10) / 8))) for r in records]
    colors_val = [r.get("clutch_sr_delta", 0.0) for r in records]
    names = [r.get("player_name", "") for r in records]
    hover = [
        f"<b>{r.get('player_name', '')}</b><br/>Score: {r.get('pressure_score', 0):.2f}<br/>P-SR: {r.get('pressure_sr', 0):.1f}<br/>P-Balls: {r.get('pressure_balls_faced', 0)}<br/>P-Runs: {r.get('pressure_runs', 0)}<br/>Clutch Δ: {r.get('clutch_sr_delta', 0):+.1f}"
        for r in records
    ]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        mode="markers+text",
        marker=dict(
            size=sizes,
            color=colors_val,
            colorscale="Viridis",
            showscale=True,
            colorbar=dict(title="Clutch Δ"),
            line=dict(width=1, color=RR_NAVY),
        ),
        text=names,
        textposition="top center",
        hovertext=hover,
        hoverinfo="text",
    ))
    fig.update_layout(
        title="Batting Clutch Landscape: Strike Rate vs Pressure Score (Bubble size = Pressure Balls Faced)",
        xaxis_title="High-Pressure Strike Rate",
        yaxis_title="Composite Pressure Score",
        template="plotly_white",
        height=450,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def plot_bowling_scatter(records: list[dict[str, Any]]) -> go.Figure:
    """Plot Bowler Pressure Economy vs Pressure Score with wicket bubbles."""
    x = [r.get("pressure_econ", 0.0) for r in records]
    y = [r.get("pressure_score", 0.0) for r in records]
    sizes = [max(8, min(30, int(r.get("pressure_wkts", 1) * 2.5))) for r in records]
    colors_val = [r.get("clutch_econ_delta", 0.0) for r in records]
    names = [r.get("player_name", "") for r in records]
    hover = [
        f"<b>{r.get('player_name', '')}</b><br/>Score: {r.get('pressure_score', 0):.2f}<br/>P-Econ: {r.get('pressure_econ', 0):.2f}<br/>P-Balls: {r.get('pressure_legal_balls', 0)}<br/>P-Wkts: {r.get('pressure_wkts', 0)}<br/>Clutch Tightening Δ: {r.get('clutch_econ_delta', 0):+.2f}"
        for r in records
    ]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        mode="markers+text",
        marker=dict(
            size=sizes,
            color=colors_val,
            colorscale="Plasma_r",
            showscale=True,
            colorbar=dict(title="Tightening Δ"),
            line=dict(width=1, color=RR_NAVY),
        ),
        text=names,
        textposition="top center",
        hovertext=hover,
        hoverinfo="text",
    ))
    fig.update_layout(
        title="Bowling Stranglehold Landscape: Economy vs Pressure Score (Bubble size = Pressure Wickets)",
        xaxis_title="High-Pressure Economy Rate (Lower is Better)",
        yaxis_title="Composite Pressure Score",
        template="plotly_white",
        height=450,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def plot_player_phase_bars(profile: dict[str, Any], discipline: str) -> go.Figure:
    """Plot player phase-wise performance under pressure."""
    if discipline == "Batting":
        phases = ["Powerplay", "Middle", "Death", "Chase", "1st Innings"]
        vals = [
            profile["batting"]["pp_p_sr"],
            profile["batting"]["mid_p_sr"],
            profile["batting"]["death_p_sr"],
            profile["batting"]["chase_p_sr"],
            profile["batting"]["inn1_p_sr"],
        ]
        balls = [
            profile["batting"]["pp_p_bf"],
            profile["batting"]["mid_p_bf"],
            profile["batting"]["death_p_bf"],
            profile["batting"]["chase_p_bf"],
            profile["batting"]["inn1_p_bf"],
        ]
        y_label = "Pressure Strike Rate"
        color = RR_PINK
    else:
        phases = ["Powerplay", "Middle", "Death"]
        vals = [
            profile["bowling"]["pp_p_econ"],
            profile["bowling"]["mid_p_econ"],
            profile["bowling"]["death_p_econ"],
        ]
        balls = [
            profile["bowling"]["pp_p_balls"],
            profile["bowling"]["mid_p_balls"],
            profile["bowling"]["death_p_balls"],
        ]
        y_label = "Pressure Economy Rate"
        color = RR_NAVY

    text = [f"{v:.1f} ({b}b)" if b > 0 else "N/A" for v, b in zip(vals, balls)]

    fig = go.Figure(data=[
        go.Bar(
            x=phases,
            y=vals,
            marker_color=color,
            text=text,
            textposition="auto",
        )
    ])
    fig.update_layout(
        title=f"Situational & Phase Breakdown under High Pressure (P ≥ 50)",
        xaxis_title="Phase / Context",
        yaxis_title=y_label,
        template="plotly_white",
        height=320,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def plot_comparison_bars(players: list[dict[str, Any]], discipline: str) -> go.Figure:
    """Plot multi-player metric comparison bar chart."""
    names = [p.get("player_name", "") for p in players]
    fig = go.Figure()
    if discipline == "Batting":
        psr = [p.get("pressure_sr", 0.0) for p in players]
        csr = [p.get("overall_sr", p.get("career_sr", 0.0)) for p in players]
        fig.add_trace(go.Bar(name="Pressure SR", x=names, y=psr, marker_color=RR_PINK))
        fig.add_trace(go.Bar(name="Career SR", x=names, y=csr, marker_color=RR_BLUE))
        fig.update_layout(title="Strike Rate Comparison: Pressure vs Career Baseline", barmode="group", yaxis_title="Strike Rate")
    else:
        pecon = [p.get("pressure_econ", 0.0) for p in players]
        cecon = [p.get("overall_econ", p.get("career_econ", 0.0)) for p in players]
        fig.add_trace(go.Bar(name="Pressure Econ", x=names, y=pecon, marker_color=RR_PINK))
        fig.add_trace(go.Bar(name="Career Econ", x=names, y=cecon, marker_color=RR_NAVY))
        fig.update_layout(title="Economy Comparison: Pressure vs Career Baseline", barmode="group", yaxis_title="Economy Rate (Lower is Better)")

    fig.update_layout(template="plotly_white", height=350, margin=dict(l=20, r=20, t=40, b=20))
    return fig
