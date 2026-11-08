"""
RR ScoutIQ — Environment & Initialization Test Suite
Verifies project foundation, path configuration, directories, and dependencies.
"""

from pathlib import Path
import pytest
from config.settings import (
    PROJECT_NAME,
    FULL_NAME,
    COMPETITION,
    DEADLINE,
    APP_VERSION,
    PROJECT_ROOT,
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
    REQUIRED_DIRECTORIES,
)


def test_project_configuration_loads():
    """Verify that project metadata and base configuration load correctly."""
    assert PROJECT_NAME == "RR ScoutIQ"
    assert FULL_NAME == "Cricket Talent Intelligence & Auction Decision Platform"
    assert "Rajasthan Royals" in COMPETITION
    assert DEADLINE == "18 November 2026"
    assert isinstance(APP_VERSION, str) and len(APP_VERSION) > 0
    assert isinstance(PROJECT_ROOT, Path)
    assert PROJECT_ROOT.exists() and PROJECT_ROOT.is_dir()


def test_required_directories_exist():
    """Verify that all core project directories are established on the filesystem."""
    for directory in REQUIRED_DIRECTORIES:
        assert directory.exists(), f"Required directory missing: {directory}"
        assert directory.is_dir(), f"Path is not a directory: {directory}"


def test_application_entrypoint_exists():
    """Verify that the Streamlit application entry point exists and is non-empty."""
    app_file = PROJECT_ROOT / "app.py"
    assert app_file.exists(), f"Entrypoint app.py missing at: {app_file}"
    assert app_file.is_file(), "app.py is not a regular file"
    assert app_file.stat().st_size > 0, "app.py is empty"


def test_requirements_file_exists():
    """Verify that requirements.txt exists and contains all required packages."""
    req_file = PROJECT_ROOT / "requirements.txt"
    assert req_file.exists(), f"requirements.txt missing at: {req_file}"
    assert req_file.is_file(), "requirements.txt is not a regular file"

    content = req_file.read_text(encoding="utf-8").lower()
    required_packages = [
        "streamlit",
        "pandas",
        "numpy",
        "duckdb",
        "pyarrow",
        "plotly",
        "scipy",
        "statsmodels",
        "scikit-learn",
        "pandera",
        "pytest",
        "openpyxl",
        "xlsxwriter",
        "reportlab",
        "python-dotenv",
    ]
    for pkg in required_packages:
        assert pkg in content, f"Required package '{pkg}' missing from requirements.txt"


def test_data_directories_configured_correctly():
    """Verify data directory structure, subdirectories, and .gitkeep protection."""
    data_subdirs = [
        RAW_DATA_DIR,
        INTERIM_DATA_DIR,
        PROCESSED_DATA_DIR,
        REFERENCE_DATA_DIR,
    ]
    for subdir in data_subdirs:
        assert subdir.exists(), f"Data subdirectory missing: {subdir}"
        assert subdir.parent == DATA_DIR, f"{subdir} is not a child of {DATA_DIR}"
        gitkeep = subdir / ".gitkeep"
        assert gitkeep.exists(), f".gitkeep missing in: {subdir}"


def test_artifact_directories_configured_correctly():
    """Verify artifact directory structure and .gitkeep preservation."""
    artifact_subdirs = [
        FIGURES_DIR,
        REPORTS_DIR,
        MODEL_OUTPUTS_DIR,
    ]
    for subdir in artifact_subdirs:
        assert subdir.exists(), f"Artifact subdirectory missing: {subdir}"
        assert subdir.parent == ARTIFACTS_DIR, f"{subdir} is not a child of {ARTIFACTS_DIR}"
        gitkeep = subdir / ".gitkeep"
        assert gitkeep.exists(), f".gitkeep missing in: {subdir}"


def test_src_subpackages_structure():
    """Verify modular architecture packages have __init__.py files."""
    expected_subpackages = [
        "ingestion",
        "preprocessing",
        "analytics",
        "evaluation",
        "models",
        "scouting",
        "reporting",
        "utils",
    ]
    for pkg_name in expected_subpackages:
        pkg_dir = SRC_DIR / pkg_name
        assert pkg_dir.exists(), f"Source subpackage missing: {pkg_dir}"
        init_file = pkg_dir / "__init__.py"
        assert init_file.exists(), f"__init__.py missing in: {pkg_dir}"
