# RR ScoutIQ — Cricket Talent Intelligence & Auction Decision Platform

> **SupeRR Selector Season 2 — Rajasthan Royals IPL 2027 Auction Strategy**  
> **Submission Deadline:** 18 November 2026  
> **Target Environment:** Windows 11 | Python >=3.12 | Streamlit | DuckDB

---

## 1. Project Overview

**RR ScoutIQ** is an advanced talent intelligence and auction strategy platform designed specifically for the Rajasthan Royals management, analytics wing, and scouting team ahead of the IPL 2027 Mega/Mini Auction cycle.

The platform provides end-to-end analytical infrastructure:
1. **Data Ingestion & Integrity:** Ingesting ball-by-ball event feeds, match registries, and player bio-data into embedded high-performance columnar storage.
2. **Contextual Normalization:** Phase-of-play splits (Powerplay, Middle Overs, Death), pitch index adjustments, and opposition quality weighting.
3. **Advanced Cricket Analytics:** Valuation metrics (xR, xW, True Run Rate, True Economy, Leverage Index).
4. **Talent Scouting & Role Fit:** Multidimensional profiling and domestic translation modeling (e.g., Syed Mushtaq Ali Trophy to IPL translatability).
5. **Auction War-Room Decision Engine:** Dynamic price prediction, purse optimization, replacement baseline comparisons, and live bidding scenario simulations.

---

## 2. Technology Stack

| Layer | Component | Description |
| :--- | :--- | :--- |
| **Operating System** | Windows 11 | Host operating system environment |
| **Language** | Python 3.12+ | Core runtime environment |
| **Frontend Framework** | Streamlit | Real-time interactive analytical dashboard |
| **Storage Engine** | DuckDB & PyArrow | In-process OLAP database & Arrow columnar format |
| **Data Processing** | Pandas, NumPy | Dataframe manipulation, matrix algebra |
| **Data Validation** | Pandera | Statistical schema enforcement & data contract validation |
| **Scientific & ML** | SciPy, Statsmodels, Scikit-learn | Statistical distributions, regression, clustering |
| **Visualizations** | Plotly | Interactive charts, scatter plots, radar/spider profiles |
| **Export Engines** | OpenPyXL, XlsxWriter, ReportLab | Automated war-room Excel books & PDF scouting dossiers |
| **Quality Assurance** | Pytest | Test suite and regression verification |

---

## 3. Project Structure

```
RR_ScoutIQ/
│
├── app.py                      # Main Streamlit dashboard application entry point
├── requirements.txt            # Project dependency specifications
├── README.md                   # Comprehensive technical documentation
├── .gitignore                  # Git ignore rules ensuring data security
├── .env.example                # Safe environment configuration template
│
├── config/                     # Configuration management
│   ├── __init__.py
│   └── settings.py             # Centralized paths, application metadata, constants
│
├── data/                       # Structured data directory hierarchy
│   ├── raw/                    # Raw external datasets (git-ignored)
│   ├── interim/                # Cleaned, standardized intermediate data (git-ignored)
│   ├── processed/              # Feature-engineered analytical datasets (git-ignored)
│   └── reference/              # Static reference registries, lookup tables, venue mappings
│
├── src/                        # Modular application source code
│   ├── __init__.py
│   ├── ingestion/              # Ingestion pipelines for event data and registries
│   ├── preprocessing/          # Schema enforcement, cleaning, phase definitions
│   ├── analytics/              # Performance metric calculations and splits
│   ├── evaluation/             # Player profiling, peer benchmarking, role indices
│   ├── models/                 # Price forecasting models and statistical projections
│   ├── scouting/               # Talent identification, watchlists, scouting notes
│   ├── reporting/              # PDF dossier generators and Excel exports
│   └── utils/                  # Common utilities: logging, DuckDB I/O, helpers
│
├── dashboard/                  # Streamlit view modules and visual components
│   └── __init__.py
│
├── tests/                      # Automated test suite
│   ├── __init__.py
│   └── test_environment.py    # Environment and setup verification tests
│
└── artifacts/                  # Generated analytical outputs
    ├── figures/                # Exported charts and visual assets
    ├── reports/                # Generated scouting dossiers and PDF briefings
    └── model_outputs/          # Model weights, serialized pipelines, forecasts
```

---

## 4. Setup & Installation (Windows PowerShell)

Follow the exact steps below in Windows PowerShell to initialize and activate the project environment.

### 4.1 Clone or Navigate to the Repository

```powershell
# Navigate to the project root directory
Set-Location -Path "c:\Users\ASUS\Downloads\RR_"
```

### 4.2 Create Virtual Environment

Ensure you are using Python 3.12+ (or your installed Python runtime):

```powershell
# Create an isolated virtual environment named .venv
python -m venv .venv
```

### 4.3 Activate Virtual Environment

```powershell
# If script execution is restricted on Windows:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1
```

*Verification:* Your prompt will now display `(.venv)`.

### 4.4 Install Dependencies

```powershell
# Upgrade pip to latest version
python -m pip install --upgrade pip

# Install project requirements
pip install -r requirements.txt
```

### 4.5 Configure Environment Variables

```powershell
# Create your local .env configuration from the template
Copy-Item -Path .env.example -Destination .env
```

---

## 5. Running the Application

To start the interactive Streamlit dashboard:

```powershell
# Launch Streamlit with the project entrypoint
streamlit run app.py
```

Streamlit will launch local server at:
- **Local URL:** `http://localhost:8501`
- **Network URL:** `http://<your-ip>:8501`

---

## 6. Running Tests

Execute the automated test suite with pytest:

```powershell
# Run all verification tests
pytest -v tests/test_environment.py
```

---

## 7. Data Security & Governance Policy

> **CRITICAL SECURITY NOTICE: NEVER UPLOAD PROPRIETARY DATA**

1. **Strict Git Exclusion:** The `.gitignore` configuration explicitly ignores `data/raw/*`, `data/interim/*`, `data/processed/*`, `*.duckdb`, and local `.env` secrets.
2. **Empty Directory Preservation:** All data and artifact directories contain `.gitkeep` files to retain repository structure without tracking proprietary files.
3. **No Hardcoded Credentials:** Real API tokens, database connections, and proprietary credentials must never be committed to code or examples. Use environment variables managed via local `.env`.
4. **Rajasthan Royals Proprietary Assets:** All internal scouting notes, proprietary player ratings, and private team strategy documents must remain strictly local.

---

## 8. Current Development Status

- [x] **Task 01: Project Initialization & Environment Setup** (Completed)
  - Directory structure and modular subsystem hierarchy created.
  - Configuration management centralized with `pathlib` in `config/settings.py`.
  - Dependencies pinned and tested in `requirements.txt`.
  - Git repository initialized with security rules in `.gitignore`.
  - Streamlit entrypoint created in `app.py` (restrained analytics style, no fake data).
  - Environment test suite created in `tests/test_environment.py`.
- [ ] **Task 02: Data Ingestion & Quality Control** (Pending)
- [ ] **Task 03: Feature Engineering & Contextual Normalization** (Pending)
- [ ] **Task 04: Advanced Analytics & Valuation Models** (Pending)
- [ ] **Task 05: Scouting Dashboard & War-Room Intelligence** (Pending)
