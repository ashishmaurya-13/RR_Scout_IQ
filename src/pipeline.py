"""
RR ScoutIQ — Unified End-to-End Analytical Pipeline
Orchestrates data verification, canonical database loading, pressure calculation,
player evaluation, ranking generation, and final report/export artifact creation.
"""

from __future__ import annotations
import sys
import time
from pathlib import Path

from config.settings import ARTIFACTS_DIR, DUCKDB_PATH, RAW_EXTRACTED_DIR
from src.analytics.pressure_engine import materialize_delivery_pressure_table
from src.ingestion.database import get_duckdb_connection, initialize_schema
from src.ingestion.load_data import load_all_tables
from src.preprocessing.delivery_context import materialize_delivery_context_table
from src.reporting.excel_export import generate_excel_export
from src.reporting.pdf_report import generate_pdf_report
from src.scouting.ranking_engine import RankingEngine


def run_full_pipeline(rebuild_canonical: bool = False) -> bool:
    """Run complete end-to-end RR ScoutIQ analytical pipeline.

    Args:
        rebuild_canonical: If True, completely re-ingests raw CSVs into DuckDB. Defaults to False.

    Returns:
        True if all stages completed successfully, False otherwise.
    """
    start_time = time.time()
    print("=" * 75)
    print("RR ScoutIQ — COMPLETE REPRODUCIBLE ANALYTICAL PIPELINE")
    print("Rajasthan Royals IPL 2027 Auction Strategy • SupeRR Selector Season 2")
    print("=" * 75)

    # Stage 1: Verify raw data
    print("\n[STAGE 1/6] Verifying Source Raw Datasets...")
    required_csvs = [
        "matches.csv", "ball_by_ball.csv", "playing_eleven.csv",
        "teams.csv", "competitions.csv", "competition_team_player_mapping.csv"
    ]
    for csv_file in required_csvs:
        p = RAW_EXTRACTED_DIR / csv_file
        if not p.exists() or p.stat().st_size == 0:
            print(f"  [ERROR] Missing or empty source CSV: {p}")
            return False
        print(f"  [OK] Found {csv_file:<35} ({p.stat().st_size:,} bytes)")

    # Stage 2: Canonical Database Check or Rebuild
    print("\n[STAGE 2/6] Canonical Analytical Database Verification...")
    if rebuild_canonical or not DUCKDB_PATH.exists():
        print(f"  Rebuilding database from scratch at: {DUCKDB_PATH}")
        con = get_duckdb_connection(DUCKDB_PATH, read_only=False)
        initialize_schema(con)
        load_all_tables(con, RAW_EXTRACTED_DIR)
        materialize_delivery_context_table(con)
        con.close()
    else:
        print(f"  [OK] Using verified existing canonical database: {DUCKDB_PATH}")

    # Stage 3: Materialize Continuous Pressure Engine
    print("\n[STAGE 3/6] Materializing Audited Continuous Pressure Engine...")
    con = get_duckdb_connection(DUCKDB_PATH, read_only=False)
    p_rows = materialize_delivery_pressure_table(con)
    print(f"  [OK] Successfully materialized fact_delivery_pressure: {p_rows:,} deliveries scored")

    # Stage 4: Run Ranking Engine and Export Analytics Artifacts
    print("\n[STAGE 4/6] Computing Bayesian Player Evaluations & Generating Artifacts...")
    engine = RankingEngine(con)
    artifacts = engine.export_all_artifacts()
    for name, path in artifacts.items():
        size = Path(path).stat().st_size
        print(f"  [OK] Exported {name:<26} -> {size:>7,} bytes")

    # Stage 5: Multi-Sheet Excel Export
    print("\n[STAGE 5/6] Generating Comprehensive Excel Export...")
    excel_path = generate_excel_export(con=con)
    print(f"  [OK] Created Excel Workbook -> {excel_path.stat().st_size:,} bytes")

    # Stage 6: Final Competition PDF Report
    print("\n[STAGE 6/6] Compiling Publication-Quality PDF Research Report...")
    pdf_path = generate_pdf_report(con=con)
    print(f"  [OK] Compiled Final PDF Report -> {pdf_path.stat().st_size:,} bytes")

    con.close()
    elapsed = time.time() - start_time
    print("\n" + "=" * 75)
    print(f"PIPELINE EXECUTION COMPLETED SUCCESSFULLY in {elapsed:.2f} seconds!")
    print("=" * 75)
    return True


if __name__ == "__main__":
    rebuild = "--rebuild" in sys.argv
    success = run_full_pipeline(rebuild_canonical=rebuild)
    if not success:
        sys.exit(1)
