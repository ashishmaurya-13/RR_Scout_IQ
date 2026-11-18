"""
RR ScoutIQ — Theme & Styling Configuration
Rajasthan Royals-inspired visual identity: Royal Pink, Deep Navy, crisp neutral cards.
"""

# Color Palette Constants
RR_PINK = "#E6007E"
RR_PINK_HOVER = "#C2006A"
RR_NAVY = "#001C55"
RR_NAVY_DARK = "#0A192F"
RR_BLUE = "#004BA0"
RR_GOLD = "#F59E0B"
RR_GREEN = "#10B981"
RR_GRAY_LIGHT = "#F8FAFC"
RR_BORDER = "#E2E8F0"
RR_TEXT_MAIN = "#0F172A"
RR_TEXT_MUTED = "#64748B"

CUSTOM_CSS = f"""
<style>
    /* Global Container Adjustments */
    .block-container {{
        padding-top: 1.5rem;
        padding-bottom: 2.5rem;
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 1380px;
    }}

    /* Main Branding Header */
    .rr-header-container {{
        background: linear-gradient(135deg, {RR_NAVY} 0%, {RR_NAVY_DARK} 60%, #170826 100%);
        border-radius: 12px;
        padding: 24px 32px;
        margin-bottom: 24px;
        border-bottom: 4px solid {RR_PINK};
        box-shadow: 0 4px 20px rgba(0, 28, 85, 0.25);
    }}
    .rr-header-title {{
        color: #FFFFFF !important;
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
    }}
    .rr-header-title span {{
        color: {RR_PINK};
    }}
    .rr-header-subtitle {{
        color: #94A3B8 !important;
        font-size: 1.05rem;
        font-weight: 400;
        margin-top: 6px;
        margin-bottom: 0;
    }}
    .rr-header-badge {{
        display: inline-block;
        background: rgba(230, 0, 126, 0.2);
        color: #FF80BF;
        border: 1px solid rgba(230, 0, 126, 0.4);
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 10px;
    }}

    /* KPI Cards */
    .kpi-card {{
        background: #FFFFFF;
        border: 1px solid {RR_BORDER};
        border-radius: 10px;
        padding: 18px 20px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        height: 100%;
    }}
    .kpi-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 28, 85, 0.08);
        border-color: {RR_PINK};
    }}
    .kpi-label {{
        color: {RR_TEXT_MUTED};
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }}
    .kpi-value {{
        color: {RR_NAVY};
        font-size: 1.9rem;
        font-weight: 800;
        margin: 0;
        line-height: 1.2;
    }}
    .kpi-subtext {{
        color: {RR_TEXT_MUTED};
        font-size: 0.8rem;
        margin-top: 6px;
    }}
    .kpi-delta-pos {{
        color: #059669;
        font-weight: 600;
    }}
    .kpi-delta-neg {{
        color: #DC2626;
        font-weight: 600;
    }}

    /* Player Profile Cards */
    .player-card {{
        background: #FFFFFF;
        border: 1px solid {RR_BORDER};
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
    }}
    .player-rank-badge {{
        background: {RR_PINK};
        color: #FFFFFF;
        font-size: 1.1rem;
        font-weight: 800;
        width: 38px;
        height: 38px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        margin-right: 12px;
    }}

    /* Confidence Badges */
    .badge-high {{
        background: #DEF7EC;
        color: #03543F;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
    }}
    .badge-moderate {{
        background: #FEF08A;
        color: #713F12;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
    }}
    .badge-low {{
        background: #FEE2E2;
        color: #991B1B;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
    }}

    /* Custom Responsive RR Table */
    .rr-table {{
        width: 100%;
        border-collapse: collapse;
        margin: 12px 0 20px 0;
        font-size: 0.88rem;
        background: #FFFFFF;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }}
    .rr-table th {{
        background: #001C55;
        color: #FFFFFF;
        text-align: left;
        padding: 10px 12px;
        font-weight: 600;
        border-bottom: 2px solid #E6007E;
    }}
    .rr-table td {{
        padding: 9px 12px;
        border-bottom: 1px solid #E2E8F0;
        color: #0F172A;
    }}
    .rr-table tr:hover td {{
        background-color: #F8FAFC;
    }}
    .rr-table tr:nth-child(even) td {{
        background-color: #FBFDFE;
    }}

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {{
        background-color: #0B192C;
    }}
    section[data-testid="stSidebar"] .stRadio label {{
        color: #E2E8F0 !important;
        font-weight: 500;
    }}
</style>
"""
