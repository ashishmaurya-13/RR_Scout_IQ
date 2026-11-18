"""
RR ScoutIQ — Excel Comprehensive Workbook Export
Generates multi-sheet Excel file containing all primary and supplementary leaderboards,
methodology parameters, and sensitivity analysis results.
"""

from __future__ import annotations
import json
from pathlib import Path
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from config.settings import ARTIFACTS_DIR, DUCKDB_PATH
from src.ingestion.database import get_duckdb_connection
from src.scouting.ranking_engine import RankingEngine


def generate_excel_export(out_path: Path | None = None, con: duckdb.DuckDBPyConnection | None = None) -> Path:
    """Generate multi-tab certified Excel export for Rajasthan Royals Auction Think-Tank.

    Args:
        out_path: Destination path for Excel file.
        con: Optional existing DuckDB connection.

    Returns:
        Path of created Excel workbook.
    """
    dest = out_path or (ARTIFACTS_DIR / "reports" / "final" / "RR_ScoutIQ_Full_Data_Export.xlsx")
    dest.parent.mkdir(parents=True, exist_ok=True)

    owns_con = False
    if con is None:
        con = get_duckdb_connection(DUCKDB_PATH, read_only=True)
        owns_con = True

    engine = RankingEngine(con)

    # 1. Fetch data
    top10_bat_ipl = engine.score_all_batters(min_balls=60, competition_scope="ipl")[:10]
    top10_bowl_ipl = engine.score_all_bowlers(min_balls=60, competition_scope="ipl")[:10]
    top10_bat_all = engine.score_all_batters(min_balls=60, competition_scope="all")[:10]
    top10_bowl_all = engine.score_all_bowlers(min_balls=60, competition_scope="all")[:10]
    all_bats = engine.score_all_batters(min_balls=45, competition_scope="ipl")
    all_bowls = engine.score_all_bowlers(min_balls=45, competition_scope="ipl")
    sensitivity = engine.run_sensitivity_analysis()

    # Model parameters
    val_json_path = ARTIFACTS_DIR / "analytics" / "model_validation.json"
    with val_json_path.open("r", encoding="utf-8") as f:
        val_data = json.load(f)

    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    # Styles
    navy_fill = PatternFill(start_color="001C55", end_color="001C55", fill_type="solid")
    pink_fill = PatternFill(start_color="E6007E", end_color="E6007E", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=10)
    thin_border = Border(
        left=Side(style="thin", color="D1D5DB"),
        right=Side(style="thin", color="D1D5DB"),
        top=Side(style="thin", color="D1D5DB"),
        bottom=Side(style="thin", color="D1D5DB"),
    )

    def write_sheet(title: str, rows: list[dict[str, Any]], fill=navy_fill) -> None:
        if not rows:
            return
        ws = wb.create_sheet(title=title[:31])
        headers = list(rows[0].keys())

        # Write Header
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=h.replace("_", " ").title())
            cell.fill = fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        # Write Data
        for row_idx, r in enumerate(rows, 2):
            for col_idx, h in enumerate(headers, 1):
                val = r[h]
                if isinstance(val, float):
                    val = round(val, 2)
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.font = data_font
                cell.border = thin_border
                if isinstance(val, (int, float)):
                    cell.alignment = Alignment(horizontal="right")
                else:
                    cell.alignment = Alignment(horizontal="left")

        # Auto column width
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = min(40, max(max_len + 3, 12))

    write_sheet("Top 10 Batters (IPL)", top10_bat_ipl, pink_fill)
    write_sheet("Top 10 Bowlers (IPL)", top10_bowl_ipl, navy_fill)
    write_sheet("Top 10 Batters (All T20)", top10_bat_all, pink_fill)
    write_sheet("Top 10 Bowlers (All T20)", top10_bowl_all, navy_fill)
    write_sheet("All Qualified Batters", all_bats, navy_fill)
    write_sheet("All Qualified Bowlers", all_bowls, navy_fill)
    write_sheet("Ranking Sensitivity", sensitivity, navy_fill)

    # Parameters sheet
    ws_params = wb.create_sheet(title="Model Parameters")
    ws_params.cell(row=1, column=1, value="Parameter").fill = navy_fill
    ws_params.cell(row=1, column=1).font = header_font
    ws_params.cell(row=1, column=2, value="Value").fill = navy_fill
    ws_params.cell(row=1, column=2).font = header_font

    r_idx = 2
    for k, v in val_data.get("population_parameters", {}).items():
        ws_params.cell(row=r_idx, column=1, value=k.replace("_", " ").title()).font = data_font
        ws_params.cell(row=r_idx, column=2, value=str(v)).font = data_font
        r_idx += 1

    wb.save(dest)
    if owns_con:
        con.close()
    return dest


if __name__ == "__main__":
    p = generate_excel_export()
    print(f"Generated Excel workbook at: {p}")
