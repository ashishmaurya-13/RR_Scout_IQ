"""
RR ScoutIQ — Configuration & Settings Module
Centralizes project paths, application metadata, and system configuration.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Base Directory Resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load environment variables from .env if present
load_dotenv(PROJECT_ROOT / ".env")

# Project Metadata
PROJECT_NAME = "RR ScoutIQ"
FULL_NAME = "Cricket Talent Intelligence & Auction Decision Platform"
COMPETITION = "SupeRR Selector Season 2 — Rajasthan Royals IPL 2027 Auction Strategy"
DEADLINE = "18 November 2026"
APP_VERSION = "0.1.0"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Data Directories
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
REFERENCE_DATA_DIR = DATA_DIR / "reference"

# Database Configuration
DUCKDB_PATH = PROJECT_ROOT / os.getenv("DUCKDB_PATH", "data/scout_iq.duckdb")

# Artifact Directories
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
FIGURES_DIR = ARTIFACTS_DIR / "figures"
REPORTS_DIR = ARTIFACTS_DIR / "reports"
MODEL_OUTPUTS_DIR = ARTIFACTS_DIR / "model_outputs"

# Source & Dashboard Directories
SRC_DIR = PROJECT_ROOT / "src"
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"
TESTS_DIR = PROJECT_ROOT / "tests"

# Required Directory Registry for Health Checks
REQUIRED_DIRECTORIES = [
    DATA_DIR,
    RAW_DATA_DIR,
    INTERIM_DATA_DIR,
    PROCESSED_DATA_DIR,
    REFERENCE_DATA_DIR,
    ARTIFACTS_DIR,
    FIGURES_DIR,
    REPORTS_DIR,
    MODEL_OUTPUTS_DIR,
    SRC_DIR,
    DASHBOARD_DIR,
    TESTS_DIR,
]
