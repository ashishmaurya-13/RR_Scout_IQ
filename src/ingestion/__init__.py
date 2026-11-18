"""
Ingestion Subsystem
Responsible for archive inspection, safe extraction, dataset profiling,
and parsing match event feeds, ball-by-ball logs, and auction master registries.
"""

from .archive_extractor import (
    ArchiveEntry,
    extract_data_pack,
    find_data_pack_archive,
    inventory_zip_archive,
    is_ignored_member,
)
from .database import (
    get_duckdb_connection,
    initialize_schema,
)
from .load_data import (
    IngestionPipelineReport,
    IngestionTableResult,
    load_all_tables,
    validate_database_relationships,
)
from .profiler import (
    ColumnProfile,
    KeyCheckResult,
    TableProfile,
    build_data_dictionary_rows,
    check_candidate_key,
    check_foreign_key_coverage,
    profile_column,
    profile_csv_file,
    quote_ident,
    write_data_dictionary_csv,
)

__all__ = [
    "ArchiveEntry",
    "ColumnProfile",
    "IngestionPipelineReport",
    "IngestionTableResult",
    "KeyCheckResult",
    "TableProfile",
    "build_data_dictionary_rows",
    "check_candidate_key",
    "check_foreign_key_coverage",
    "extract_data_pack",
    "find_data_pack_archive",
    "get_duckdb_connection",
    "initialize_schema",
    "inventory_zip_archive",
    "is_ignored_member",
    "load_all_tables",
    "profile_column",
    "profile_csv_file",
    "quote_ident",
    "validate_database_relationships",
    "write_data_dictionary_csv",
]
