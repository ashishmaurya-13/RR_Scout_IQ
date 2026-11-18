# RR ScoutIQ — Cricket Talent Intelligence & Auction Decision Platform

> **Official Competition Entry:** SupeRR Selector Season 2 — Rajasthan Royals IPL 2027 Auction Strategy  
> **Challenge:** Identify the Most Reliable Players Under Pressure  
> **Target Environment:** Windows 11 | Python >=3.12 | DuckDB | Streamlit | Plotly | ReportLab  
> **Deliverables:** Top 10 Batters, Top 10 Bowlers, Full Methodology Report, Interactive Streamlit Platform, Multi-Tab Excel Dossier, Publication PDF

---

## 1. Executive Summary & Official Challenge

**RR ScoutIQ** is an institutional-grade cricket analytics and talent intelligence platform engineered specifically for the **Rajasthan Royals** auction think-tank ahead of the IPL 2027 Auction cycle.

The platform addresses the official Round 1 challenge:
> **Identify the Most Reliable Players Under Pressure**  
> 1. Top 10 Batters performing consistently under pressure.  
> 2. Top 10 Bowlers performing consistently under pressure.  
> 3. A reproducible, scientifically defensible methodology explaining calculations, assumptions, and validation.

### Certified Top 10 Leaderboards (Primary: IPL Environment, Min 60 Pressure Balls)

#### Top 10 Batters Under Pressure (IPL Environment)
| Rank | Player Name | Role | Pressure Score | 90% Bayesian CI | P-Balls | P-Runs | P-SR | Shrunk SR | Career SR | Clutch Δ | Dot % | Bnd % | Runs/Out |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **Liam Livingstone** | Batting Allrounder | **64.25** | [183.0, 199.3] | 147 | 288 | 195.92 | 184.44 | 159.53 | +36.39 | 28.6% | 27.9% | 48.0 |
| **2** | **Shreyas Iyer** | Top-Order Batter | **63.72** | [180.7, 203.0] | 97 | 199 | 205.15 | 186.72 | 157.52 | +47.63 | 24.7% | 29.9% | 39.8 |
| **3** | **Naman Dhir** | Batting Allrounder | **62.72** | [181.4, 203.7] | 97 | 200 | 206.19 | 187.38 | 163.97 | +42.22 | 26.8% | 29.7% | 28.6 |
| **4** | **Rinku Singh** | Middle-Order Finisher | **62.49** | [168.9, 177.3] | 345 | 599 | 173.62 | 170.56 | 150.11 | +23.51 | 24.1% | 22.0% | 49.9 |
| **5** | **Sanju Samson** | Wicketkeeper Batter | **61.96** | [175.7, 195.1] | 116 | 222 | 191.38 | 178.96 | 152.56 | +38.82 | 25.0% | 26.7% | 37.0 |
| **6** | **Jos Buttler** | Top-Order Wicketkeeper | **61.91** | [171.1, 191.9] | 100 | 187 | 187.00 | 174.67 | 149.53 | +37.47 | 21.4% | 25.5% | 46.8 |
| **7** | **David Miller** | Middle-Order Finisher | **61.60** | [170.5, 179.9] | 309 | 545 | 176.38 | 172.66 | 144.24 | +32.14 | 26.2% | 23.3% | 36.3 |
| **8** | **Nicholas Pooran** | Wicketkeeper Batter | **61.24** | [176.7, 187.4] | 267 | 493 | 184.64 | 179.25 | 167.04 | +17.60 | 32.2% | 26.6% | 35.2 |
| **9** | **Tim David** | Middle-Order Finisher | **61.21** | [180.2, 189.6] | 332 | 623 | 187.65 | 182.80 | 177.74 | +9.91 | 28.9% | 24.1% | 36.7 |
| **10** | **Dinesh Karthik** | Wicketkeeper Finisher | **60.79** | [175.7, 189.5] | 193 | 360 | 186.53 | 179.09 | 173.80 | +12.73 | 29.5% | 26.9% | 36.0 |

#### Top 10 Bowlers Under Pressure (IPL Environment)
| Rank | Player Name | Style | Role | Pressure Score | 90% Bayesian CI | P-Balls | P-Runs | P-Econ | Shrunk Econ | Career Econ | Tightening Δ | P-Wkts | Dot % | Bnd % |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **Sunil Narine** | Spin | Allrounder | **63.01** | [5.71, 6.45] | 282 | 262 | 5.57 | 6.08 | 6.86 | +1.29 | 23 | 42.9% | 9.2% |
| **2** | **Umran Malik** | Pace | Bowler | **62.16** | [6.95, 8.73] | 81 | 95 | 7.04 | 7.84 | 9.65 | +2.61 | 10 | 55.8% | 14.7% |
| **3** | **Jasprit Bumrah** | Pace | Bowler | **58.69** | [6.61, 7.47] | 241 | 266 | 6.62 | 7.04 | 7.17 | +0.55 | 18 | 40.9% | 11.2% |
| **4** | **Mitchell Santner** | Spin | Allrounder | **58.65** | [5.98, 7.50] | 100 | 89 | 5.34 | 6.74 | 7.63 | +2.29 | 5 | 39.8% | 9.2% |
| **5** | **Varun Chakravarthy** | Spin | Bowler | **57.87** | [7.48, 8.16] | 341 | 433 | 7.62 | 7.82 | 8.23 | +0.61 | 26 | 42.9% | 14.5% |
| **6** | **Eshan Malinga** | Pace | Bowler | **57.80** | [7.55, 8.71] | 146 | 189 | 7.77 | 8.13 | 9.20 | +1.43 | 16 | 36.8% | 14.9% |
| **7** | **Yuzvendra Chahal** | Spin | Bowler | **56.95** | [7.93, 8.57] | 380 | 510 | 8.05 | 8.25 | 8.76 | +0.71 | 40 | 33.6% | 15.1% |
| **8** | **Anshul Kamboj** | Pace | Bowler | **56.89** | [7.85, 9.77] | 78 | 105 | 8.08 | 8.81 | 9.97 | +1.89 | 8 | 43.4% | 15.8% |
| **9** | **Matheesha Pathirana** | Pace | Bowler | **56.43** | [7.72, 8.44] | 293 | 383 | 7.84 | 8.08 | 8.66 | +0.82 | 26 | 35.4% | 13.9% |
| **10** | **Mohammed Shami** | Pace | Bowler | **56.02** | [7.63, 8.83] | 153 | 202 | 7.92 | 8.23 | 8.73 | +0.81 | 14 | 37.7% | 15.2% |

---

## 2. Core Methodological Architecture

### 2.1 Continuous Pre-Delivery Pressure Index ($P \in [0, 100]$)

Pressure is calculated strictly on **pre-delivery information** before each ball is bowled, guaranteeing zero data leakage from delivery outcomes.

#### Chase Pressure Index ($CPI$, Innings 2 & 4)
$$\text{CPI} = \min\left(100.0, \max\left(0.0, 100 \cdot \left[ 0.55 \cdot f_{\text{rate}} + 0.30 \cdot f_{\text{wkt}} + 0.15 \cdot f_{\text{urgency}} \right] \cdot M_{\text{close}} \right)\right)$$

1. **Required Rate Pressure ($f_{\text{rate}}$):** Centered at empirical median target chase rate ($R_0 = 9.0$ RPO, steepness $k_r = 0.22$):
   $$f_{\text{rate}}(RRR) = \frac{1}{1 + e^{-0.22 \cdot (RRR - 9.0)}}$$
2. **Resource Scarcity ($f_{\text{wkt}}$):** Non-linear wicket stress:
   $$f_{\text{wkt}}(W) = 1.0 - \left(\frac{W}{10}\right)^{0.75}, \quad W \in [1, 10]$$
3. **Audited Monotonic Urgency ($f_{\text{urgency}}$):** Strictly increases as remaining balls run out:
   $$f_{\text{urgency}}(r, B) = 0.20 + 0.80 \cdot \left(1.0 - \frac{\min(r, B)}{\max(1, B)}\right)^{1.25}$$
4. **Climax Multiplier ($M_{\text{close}}$):** $1.15$ when runs required $\le 25$ and balls remaining $\le 18$.
5. **Super Over:** Innings 4 chase fixed at **95.0**; Innings 3 first innings fixed at **88.0**.

#### First-Innings Structural Pressure ($FPI$, Innings 1 & 3)
$$\text{FPI} = \min\left(100.0, \max\left(0.0, 100 \cdot \left[ 0.45 \cdot S_{\text{wkt}} + 0.20 \cdot S_{\text{stag}} + 0.35 \cdot L_{\text{phase}} \right]\right)\right)$$
- **Wicket Stress ($S_{\text{wkt}}$):** Excess wickets lost compared to empirical expected curve $E[\text{wkts} \mid b] = 6.0 \cdot (b/B)^{0.85}$.
- **Stagnation Penalty ($S_{\text{stag}}$):** Current run rate deficit below empirical median 1st innings rate ($8.34$ RPO) post-Powerplay.
- **Phase Leverage ($L_{\text{phase}}$):** Powerplay ($0.25$), Middle ($0.40$), Death overs ($0.70 \to 1.00$).

### 2.2 Bayesian Reliability Model (Empirical Bayes Shrinkage)
Under Gaussian conjugate shrinkage with empirical prior:
$$n_0 = \frac{\sigma_e^2}{\sigma_0^2} = 45.0 \text{ balls}$$
$$\hat{\theta}_i = \lambda_i \cdot X_i + (1 - \lambda_i) \cdot \mu_0, \quad \lambda_i = \frac{n_i}{n_i + n_0}$$
$$\text{CI}_{90\%} = \left[ \hat{\theta}_i - 1.645 \cdot \sigma_0 \sqrt{1 - \lambda_i}, \; \hat{\theta}_i + 1.645 \cdot \sigma_0 \sqrt{1 - \lambda_i} \right]$$

### 2.3 Volume Double-Counting Elimination
Composite Pressure Score is computed using standardized dimensions, where volume enters **solely** through Bayesian shrinkage reliability $\lambda_i$:
$$\text{Score}_{\text{bat}} = \min\left(100.0, \max\left(0.0, 50.0 + 12.0 \cdot M_{\text{bat}} \cdot \sqrt{\lambda_i}\right)\right)$$
$$\text{Score}_{\text{bowl}} = \min\left(100.0, \max\left(0.0, 50.0 + 12.0 \cdot M_{\text{bowl}} \cdot \sqrt{\lambda_i}\right)\right)$$

---

## 3. Data Population Census & Integrity Reconciliation

All figures verified through canonical DuckDB queries (`data/interim/scout_iq.duckdb`):
- **Matches:** 883 total recorded matches (867 with ball-by-ball delivery data + 16 abandoned/no-result matches without balls).
- **IPL Matches:** Exactly 371 matches (100% with delivery data).
- **Deliveries:** 200,999 total deliveries (200,896 scored deliveries; 103 deliveries with NULL pressure due to unrecorded Match 23674 DLS target).
- **Dismissals:** 10,881 total dismissal events (10,272 bowler wickets, 600 run-outs, 8 retired out, 1 obstructing the field).
- **Zero-Leakage Proof:** 100% of deliveries use strictly pre-delivery ball count, runs needed, and wickets fallen.

---

## 4. Execution & Quick Start Guide

### 4.1 Run the Full Reproducible Analytical Pipeline
Generates canonical database, materializes continuous pressure engine, computes Bayesian rankings, and exports Excel and PDF reports in ~4 seconds:
```powershell
python run_pipeline.py
```

### 4.2 Launch the Interactive Streamlit Platform
```powershell
streamlit run app.py
```
Browse to `http://localhost:8501` to access all 8 interactive platform pages:
1. **Executive Overview:** High-level KPIs, delivery distribution histogram, wicket hazard curve, top 3 showcase.
2. **Top 10 Batters:** Primary IPL leaderboard, All-T20 toggle, scatter landscape, quick scouting insights.
3. **Top 10 Bowlers:** Primary IPL leaderboard, pace/spin filters, scatter landscape, quick scouting insights.
4. **Player Intelligence:** Deep dive into any player's career, high-pressure, extreme-pressure, and phase splits.
5. **Head-to-Head Comparison:** Side-by-side multi-player evaluation, grouped bar charts, comparative summary.
6. **Pressure Analytics:** Real-time interactive match-state pressure simulator, empirical distributions.
7. **Methodology & Validation:** Mathematical formulas, 7-scenario sensitivity grid, hyperparameter audit.
8. **Data & Model Health:** Census reconciliation, zero-leakage verification, automated test status.

### 4.3 Run the Automated Test Suite
Execute all 60 unit and integration tests across data engineering, pressure modeling, and ranking sanity:
```powershell
python -m pytest -v
```

---

## 5. Artifacts & Deliverables Inventory

| Path | Format | Description |
| :--- | :---: | :--- |
| `artifacts/reports/final/RR_ScoutIQ_Final_Competition_Report.pdf` | PDF | Publication-quality 6-page official research report |
| `artifacts/reports/final/RR_ScoutIQ_Final_Competition_Report.md` | Markdown | Complete 19-section research report source |
| `artifacts/reports/final/RR_ScoutIQ_Full_Data_Export.xlsx` | Excel | Multi-tab workbook with IPL and All-T20 leaderboards |
| `artifacts/reports/final/submission_summary.md` | Markdown | Executive submission overview for RR leadership |
| `artifacts/analytics/top_10_batters_ipl.csv` | CSV | Certified Primary IPL Top 10 Batters |
| `artifacts/analytics/top_10_bowlers_ipl.csv` | CSV | Certified Primary IPL Top 10 Bowlers |
| `artifacts/analytics/ranking_sensitivity.csv` | CSV | 7-scenario sensitivity analysis grid |
| `artifacts/analytics/model_validation.json` | JSON | Parameter disclosures and calibration metadata |

---

## 6. Transparent Boundary Disclosures & Limitations

1. **Auction Availability:** The official dataset does NOT contain auction purse declarations, retention rosters, player release statuses, base prices, or player ages. All player assessments are statistical observations and tactical role fits.
2. **Sensor Boundaries:** The dataset records ball-by-ball outcomes but does NOT include ball-tracking Hawkeye trajectories, release speeds, or fielding error attribution.
3. **Sample Thresholds:** Players with $<45$ pressure balls are shrunk toward population priors and excluded from Top 10 rankings to eliminate small-sample noise.
