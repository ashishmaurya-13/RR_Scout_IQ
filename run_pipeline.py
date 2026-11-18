"""
RR ScoutIQ — Root Execution Script
Run full pipeline: python run_pipeline.py
"""

from src.pipeline import run_full_pipeline

if __name__ == "__main__":
    import sys
    rebuild = "--rebuild" in sys.argv
    run_full_pipeline(rebuild_canonical=rebuild)
