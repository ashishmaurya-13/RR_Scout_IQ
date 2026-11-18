"""
Dataset Profiling & Schema Inspection Utilities (DuckDB-Backed)

Provides reusable, read-only profiling functions for auditing CSV tables,
candidate keys, referential integrity, distributions, and data dictionaries
without requiring Pandas/PyArrow C-extensions.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import duckdb

NUMERIC_DUCKDB_PREFIXES = (
    "TINYINT",
    "SMALLINT",
    "INTEGER",
    "INT",
    "BIGINT",
    "HUGEINT",
    "UTINYINT",
    "USMALLINT",
    "UINTEGER",
    "UBIGINT",
    "FLOAT",
    "DOUBLE",
    "DECIMAL",
)
DATE_DUCKDB_TYPES = {"DATE", "TIMESTAMP", "TIMESTAMP WITH TIME ZONE"}


@dataclass(frozen=True)
class KeyCheckResult:
    """Result of evaluating uniqueness and null completeness for a candidate key."""

    columns: tuple[str, ...]
    row_count: int
    unique_count: int
    duplicate_row_count: int
    null_row_count: int
    is_unique_not_null: bool


@dataclass(frozen=True)
class ColumnProfile:
    """Comprehensive column-level statistical and structural profile."""

    table_name: str
    column_name: str
    inferred_dtype: str
    row_count: int
    non_null_count: int
    null_count: int
    null_pct: float
    unique_count: int
    sample_values: list[str]
    numeric_summary: dict[str, float | int | None] = field(default_factory=dict)
    date_summary: dict[str, str | None] = field(default_factory=dict)
    top_values: list[tuple[str, int]] = field(default_factory=list)


@dataclass(frozen=True)
class TableProfile:
    """Table-level summary profile including keys, duplicates, and columns."""

    table_name: str
    source_path: str
    file_size_bytes: int
    row_count: int
    column_count: int
    exact_duplicate_rows: int
    key_checks: list[KeyCheckResult]
    columns: list[ColumnProfile]


def quote_ident(identifier: str) -> str:
    """Safely double-quote a DuckDB SQL identifier."""
    return '"' + identifier.replace('"', '""') + '"'


def quote_literal(value: str) -> str:
    """Safely single-quote a SQL string literal for DuckDB."""
    return "'" + value.replace("'", "''") + "'"


def _is_numeric_duckdb_type(dtype: str) -> bool:
    upper = dtype.upper()
    return any(upper.startswith(prefix) for prefix in NUMERIC_DUCKDB_PREFIXES)


def _is_date_duckdb_type(dtype: str) -> bool:
    return dtype.upper() in DATE_DUCKDB_TYPES


def check_candidate_key(
    con: duckdb.DuckDBPyConnection,
    table_ident: str,
    columns: list[str],
    available_columns: set[str],
) -> KeyCheckResult:
    """Evaluate whether ``columns`` form a unique, non-null candidate key in DuckDB."""
    missing = [col for col in columns if col not in available_columns]
    if missing:
        raise KeyError(f"Columns not found in table {table_ident}: {missing}")

    quoted_cols = [quote_ident(c) for c in columns]
    col_list = ", ".join(quoted_cols)
    null_cond = " OR ".join(f"{qc} IS NULL" for qc in quoted_cols)

    row_count, null_row_count = con.execute(
        f"""
        SELECT
            COUNT(*)::BIGINT,
            COALESCE(SUM(CASE WHEN {null_cond} THEN 1 ELSE 0 END), 0)::BIGINT
        FROM {table_ident}
        """
    ).fetchone()

    unique_count, duplicate_row_count = con.execute(
        f"""
        SELECT
            COUNT(*)::BIGINT,
            COALESCE(SUM(CASE WHEN grp_cnt > 1 THEN grp_cnt ELSE 0 END), 0)::BIGINT
        FROM (
            SELECT COUNT(*) AS grp_cnt
            FROM {table_ident}
            GROUP BY {col_list}
        ) t
        """
    ).fetchone()

    return KeyCheckResult(
        columns=tuple(columns),
        row_count=int(row_count),
        unique_count=int(unique_count),
        duplicate_row_count=int(duplicate_row_count),
        null_row_count=int(null_row_count),
        is_unique_not_null=(int(duplicate_row_count) == 0 and int(null_row_count) == 0),
    )


def _summarize_numeric_column(
    con: duckdb.DuckDBPyConnection,
    table_ident: str,
    quoted_col: str,
) -> dict[str, float | int | None]:
    row = con.execute(
        f"""
        SELECT
            MIN({quoted_col})::DOUBLE,
            QUANTILE_CONT({quoted_col}, 0.25)::DOUBLE,
            MEDIAN({quoted_col})::DOUBLE,
            QUANTILE_CONT({quoted_col}, 0.75)::DOUBLE,
            MAX({quoted_col})::DOUBLE,
            AVG({quoted_col})::DOUBLE,
            STDDEV_SAMP({quoted_col})::DOUBLE,
            COALESCE(SUM(CASE WHEN {quoted_col} = 0 THEN 1 ELSE 0 END), 0)::BIGINT,
            COALESCE(SUM(CASE WHEN {quoted_col} < 0 THEN 1 ELSE 0 END), 0)::BIGINT
        FROM {table_ident}
        WHERE {quoted_col} IS NOT NULL
        """
    ).fetchone()

    if row is None or row[0] is None:
        return {
            "min": None,
            "p25": None,
            "median": None,
            "p75": None,
            "max": None,
            "mean": None,
            "std": None,
            "zero_count": 0,
            "negative_count": 0,
        }

    return {
        "min": float(row[0]),
        "p25": float(row[1]) if row[1] is not None else None,
        "median": float(row[2]) if row[2] is not None else None,
        "p75": float(row[3]) if row[3] is not None else None,
        "max": float(row[4]),
        "mean": float(row[5]) if row[5] is not None else None,
        "std": float(row[6]) if row[6] is not None else 0.0,
        "zero_count": int(row[7]),
        "negative_count": int(row[8]),
    }


def _summarize_date_column(
    con: duckdb.DuckDBPyConnection,
    table_ident: str,
    quoted_col: str,
) -> dict[str, str | None]:
    row = con.execute(
        f"""
        SELECT
            MIN({quoted_col})::VARCHAR,
            MAX({quoted_col})::VARCHAR
        FROM {table_ident}
        WHERE {quoted_col} IS NOT NULL
        """
    ).fetchone()
    if row is None:
        return {"min_date": None, "max_date": None}
    return {"min_date": row[0], "max_date": row[1]}


def profile_column(
    con: duckdb.DuckDBPyConnection,
    table_ident: str,
    table_name: str,
    column_name: str,
    inferred_dtype: str,
    row_count: int,
    top_n: int = 5,
    sample_n: int = 3,
) -> ColumnProfile:
    """Compute column metadata, missingness, cardinality, and value distributions."""
    qcol = quote_ident(column_name)
    non_null_count, unique_count = con.execute(
        f"""
        SELECT
            COUNT({qcol})::BIGINT,
            COUNT(DISTINCT {qcol})::BIGINT
        FROM {table_ident}
        """
    ).fetchone()
    non_null_count = int(non_null_count)
    null_count = row_count - non_null_count
    null_pct = round((null_count / row_count) * 100.0, 4) if row_count > 0 else 0.0

    sample_rows = con.execute(
        f"""
        SELECT DISTINCT {qcol}::VARCHAR
        FROM {table_ident}
        WHERE {qcol} IS NOT NULL
        LIMIT {int(sample_n)}
        """
    ).fetchall()
    sample_values = [r[0] for r in sample_rows]

    top_rows = con.execute(
        f"""
        SELECT {qcol}::VARCHAR AS val, COUNT(*)::BIGINT AS cnt
        FROM {table_ident}
        WHERE {qcol} IS NOT NULL
        GROUP BY {qcol}
        ORDER BY cnt DESC, val ASC
        LIMIT {int(top_n)}
        """
    ).fetchall()
    top_values = [(str(val), int(cnt)) for val, cnt in top_rows]

    numeric_summary = (
        _summarize_numeric_column(con, table_ident, qcol)
        if _is_numeric_duckdb_type(inferred_dtype)
        else {}
    )
    date_summary = (
        _summarize_date_column(con, table_ident, qcol)
        if _is_date_duckdb_type(inferred_dtype)
        else {}
    )

    return ColumnProfile(
        table_name=table_name,
        column_name=column_name,
        inferred_dtype=inferred_dtype,
        row_count=row_count,
        non_null_count=non_null_count,
        null_count=null_count,
        null_pct=null_pct,
        unique_count=int(unique_count),
        sample_values=sample_values,
        numeric_summary=numeric_summary,
        date_summary=date_summary,
        top_values=top_values,
    )


def profile_csv_file(
    csv_path: Path,
    candidate_keys: list[list[str]] | None = None,
    table_name: str | None = None,
) -> TableProfile:
    """Inspect a CSV file in read-only mode via DuckDB and return a ``TableProfile``."""
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    resolved_name = table_name or csv_path.stem
    table_ident = quote_ident(resolved_name)

    con = duckdb.connect(":memory:")
    try:
        con.execute(
            f"""
            CREATE TEMP TABLE {table_ident} AS
            SELECT * FROM read_csv_auto({quote_literal(str(csv_path))}, header=true, sample_size=-1)
            """
        )

        schema_rows = con.execute(f"DESCRIBE {table_ident}").fetchall()
        col_defs = [(str(r[0]), str(r[1])) for r in schema_rows]
        available_cols = {name for name, _ in col_defs}

        row_count = int(con.execute(f"SELECT COUNT(*)::BIGINT FROM {table_ident}").fetchone()[0])

        if col_defs:
            all_cols_sql = ", ".join(quote_ident(name) for name, _ in col_defs)
            exact_duplicates = int(
                con.execute(
                    f"""
                    SELECT COALESCE(SUM(cnt - 1), 0)::BIGINT
                    FROM (
                        SELECT COUNT(*) AS cnt
                        FROM {table_ident}
                        GROUP BY {all_cols_sql}
                        HAVING COUNT(*) > 1
                    ) d
                    """
                ).fetchone()[0]
            )
        else:
            exact_duplicates = 0

        key_results: list[KeyCheckResult] = []
        for key_cols in candidate_keys or []:
            if all(col in available_cols for col in key_cols):
                key_results.append(
                    check_candidate_key(con, table_ident, key_cols, available_cols)
                )

        col_profiles = [
            profile_column(con, table_ident, resolved_name, col_name, col_type, row_count)
            for col_name, col_type in col_defs
        ]

        return TableProfile(
            table_name=resolved_name,
            source_path=str(csv_path),
            file_size_bytes=csv_path.stat().st_size,
            row_count=row_count,
            column_count=len(col_defs),
            exact_duplicate_rows=exact_duplicates,
            key_checks=key_results,
            columns=col_profiles,
        )
    finally:
        con.close()


def build_data_dictionary_rows(
    profiles: list[TableProfile],
    descriptions: dict[tuple[str, str], str] | None = None,
) -> list[dict[str, Any]]:
    """Build flattened dictionary rows suitable for writing ``data_dictionary.csv``."""
    rows: list[dict[str, Any]] = []
    desc_map = descriptions or {}

    for table in profiles:
        pk_cols = {
            col
            for kc in table.key_checks
            if kc.is_unique_not_null
            for col in kc.columns
        }
        for col in table.columns:
            num = col.numeric_summary
            dt = col.date_summary
            top_preview = "; ".join(f"{val} ({cnt})" for val, cnt in col.top_values[:3])
            min_val = num.get("min") if num else dt.get("min_date")
            max_val = num.get("max") if num else dt.get("max_date")
            rows.append(
                {
                    "table_name": col.table_name,
                    "column_name": col.column_name,
                    "inferred_dtype": col.inferred_dtype,
                    "row_count": col.row_count,
                    "non_null_count": col.non_null_count,
                    "null_count": col.null_count,
                    "null_pct": col.null_pct,
                    "unique_count": col.unique_count,
                    "is_candidate_pk_member": col.column_name in pk_cols,
                    "min_value": min_val,
                    "median_value": num.get("median"),
                    "max_value": max_val,
                    "mean_value": (
                        round(num["mean"], 4) if num.get("mean") is not None else None
                    ),
                    "sample_values": " | ".join(col.sample_values),
                    "top_values_preview": top_preview,
                    "audit_notes": desc_map.get((col.table_name, col.column_name), ""),
                }
            )
    return rows


def write_data_dictionary_csv(
    profiles: list[TableProfile],
    output_path: Path,
    descriptions: dict[tuple[str, str], str] | None = None,
) -> Path:
    """Write ``data_dictionary.csv`` cleanly using Python's CSV writer."""
    rows = build_data_dictionary_rows(profiles, descriptions=descriptions)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "table_name",
        "column_name",
        "inferred_dtype",
        "row_count",
        "non_null_count",
        "null_count",
        "null_pct",
        "unique_count",
        "is_candidate_pk_member",
        "min_value",
        "median_value",
        "max_value",
        "mean_value",
        "sample_values",
        "top_values_preview",
        "audit_notes",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def check_foreign_key_coverage(
    child_csv: Path,
    child_col: str,
    parent_csv: Path,
    parent_col: str,
) -> dict[str, Any]:
    """Compute referential overlap and orphan counts between child and parent CSV keys."""
    q_child = quote_ident(child_col)
    q_parent = quote_ident(parent_col)

    con = duckdb.connect(":memory:")
    try:
        con.execute(
            f"CREATE TEMP TABLE child_tbl AS SELECT * FROM read_csv_auto({quote_literal(str(child_csv))}, header=true, sample_size=-1)"
        )
        con.execute(
            f"CREATE TEMP TABLE parent_tbl AS SELECT * FROM read_csv_auto({quote_literal(str(parent_csv))}, header=true, sample_size=-1)"
        )

        stats = con.execute(
            f"""
            WITH c_keys AS (
                SELECT DISTINCT {q_child} AS k FROM child_tbl WHERE {q_child} IS NOT NULL
            ),
            p_keys AS (
                SELECT DISTINCT {q_parent} AS k FROM parent_tbl WHERE {q_parent} IS NOT NULL
            )
            SELECT
                (SELECT COUNT(*) FROM child_tbl WHERE {q_child} IS NOT NULL)::BIGINT AS child_non_null_rows,
                (SELECT COUNT(*) FROM child_tbl WHERE {q_child} IS NULL)::BIGINT AS child_null_rows,
                (SELECT COUNT(*) FROM c_keys)::BIGINT AS child_unique_keys,
                (SELECT COUNT(*) FROM p_keys)::BIGINT AS parent_unique_keys,
                (SELECT COUNT(*) FROM c_keys c INNER JOIN p_keys p ON c.k = p.k)::BIGINT AS matched_keys,
                (SELECT COUNT(*) FROM c_keys c LEFT JOIN p_keys p ON c.k = p.k WHERE p.k IS NULL)::BIGINT AS orphan_child_keys,
                (SELECT COUNT(*) FROM child_tbl ch LEFT JOIN p_keys p ON ch.{q_child} = p.k WHERE ch.{q_child} IS NOT NULL AND p.k IS NULL)::BIGINT AS orphan_child_rows,
                (SELECT COUNT(*) FROM p_keys p LEFT JOIN c_keys c ON p.k = c.k WHERE c.k IS NULL)::BIGINT AS unreferenced_parent_keys
            """
        ).fetchone()

        sample_orphans = [
            str(r[0])
            for r in con.execute(
                f"""
                SELECT DISTINCT ch.{q_child}::VARCHAR AS k
                FROM child_tbl ch
                LEFT JOIN (SELECT DISTINCT {q_parent} AS k FROM parent_tbl WHERE {q_parent} IS NOT NULL) p
                ON ch.{q_child} = p.k
                WHERE ch.{q_child} IS NOT NULL AND p.k IS NULL
                ORDER BY k
                LIMIT 10
                """
            ).fetchall()
        ]
        sample_unref = [
            str(r[0])
            for r in con.execute(
                f"""
                SELECT DISTINCT p.{q_parent}::VARCHAR AS k
                FROM parent_tbl p
                LEFT JOIN (SELECT DISTINCT {q_child} AS k FROM child_tbl WHERE {q_child} IS NOT NULL) c
                ON p.{q_parent} = c.k
                WHERE p.{q_parent} IS NOT NULL AND c.k IS NULL
                ORDER BY k
                LIMIT 10
                """
            ).fetchall()
        ]

        return {
            "child_non_null_rows": int(stats[0]),
            "child_null_rows": int(stats[1]),
            "child_unique_keys": int(stats[2]),
            "parent_unique_keys": int(stats[3]),
            "matched_keys": int(stats[4]),
            "orphan_child_keys": int(stats[5]),
            "orphan_child_rows": int(stats[6]),
            "unreferenced_parent_keys": int(stats[7]),
            "sample_orphan_keys": sample_orphans,
            "sample_unreferenced_parent_keys": sample_unref,
        }
    finally:
        con.close()
