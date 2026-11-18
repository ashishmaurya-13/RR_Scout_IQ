"""
RR ScoutIQ — Analytical Database Module
Manages DuckDB database connection, schema definitions, dimensional modeling,
and canonical tables for cricket talent intelligence and pressure evaluation.
"""

from __future__ import annotations
from pathlib import Path
import duckdb
from config.settings import DUCKDB_PATH, INTERIM_DATA_DIR


def get_duckdb_connection(
    db_path: Path | str | None = None,
    read_only: bool = False,
) -> duckdb.DuckDBPyConnection:
    """Create or retrieve a DuckDB database connection.

    Args:
        db_path: Filesystem path to DuckDB database file or ':memory:'.
                 Defaults to ``DUCKDB_PATH`` (data/interim/scout_iq.duckdb).
        read_only: Whether to open database in read-only mode.

    Returns:
        Connected DuckDB connection object.
    """
    if db_path is None:
        db_path = DUCKDB_PATH

    if isinstance(db_path, str) and db_path != ":memory:":
        db_path = Path(db_path)

    if isinstance(db_path, Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_str = str(db_path)
    else:
        db_str = db_path

    return duckdb.connect(database=db_str, read_only=read_only)


SCHEMA_DDL = """
-- 1. dim_competition: Competition metadata, tournament categories, and tiering
CREATE TABLE IF NOT EXISTS dim_competition (
    comp_id BIGINT PRIMARY KEY,
    comp_name VARCHAR NOT NULL,
    match_format VARCHAR NOT NULL,
    season VARCHAR NOT NULL,
    competition_category VARCHAR NOT NULL, -- 'IPL', 'T20I', 'Other T20'
    is_tier1_competition BOOLEAN NOT NULL  -- TRUE for IPL & T20I, FALSE for developmental 'Other T20'
);

-- 2. dim_team: Team and franchise entities across competitions
CREATE TABLE IF NOT EXISTS dim_team (
    comp_id BIGINT NOT NULL,
    team_id BIGINT NOT NULL,
    team_name VARCHAR NOT NULL,
    PRIMARY KEY (comp_id, team_id)
);

-- 3. fact_match: Match-level metadata, scheduling, venues, results, and shortened-match parameters
CREATE TABLE IF NOT EXISTS fact_match (
    match_id BIGINT PRIMARY KEY,
    comp_id BIGINT NOT NULL,
    match_number BIGINT NOT NULL,
    match_date DATE NOT NULL,
    stage VARCHAR NOT NULL,
    venue_id BIGINT NOT NULL,
    venue_country VARCHAR NOT NULL,
    home_team_id BIGINT NOT NULL,
    home_team VARCHAR NOT NULL,
    away_team_id BIGINT NOT NULL,
    away_team VARCHAR NOT NULL,
    home_team_captain_id BIGINT,
    away_team_captain_id BIGINT,
    toss_win_team_id BIGINT,
    toss_opted VARCHAR,
    man_of_the_match_raw BIGINT NOT NULL,
    man_of_the_match_clean BIGINT,         -- NULL when raw is 0 sentinel
    first_inn_revised_balls BIGINT,        -- Domain-clarified: revised balls (not overs)
    second_inn_revised_balls BIGINT,       -- Domain-clarified: revised balls (not overs)
    revised_target BIGINT,                 -- DLS target runs in 2nd innings
    knock_out BIGINT NOT NULL,
    is_playoff BOOLEAN NOT NULL,           -- knock_out = 1
    win_team_id BIGINT,
    result VARCHAR NOT NULL,
    match_status VARCHAR NOT NULL,         -- 'Completed', 'No Result', 'Match Abandoned', 'Tied'
    has_delivery_data BOOLEAN NOT NULL,    -- TRUE for 867 matches with ball_by_ball records
    is_shortened_match BOOLEAN NOT NULL,   -- TRUE if rain/weather truncated innings balls
    inn1_scheduled_balls BIGINT NOT NULL,  -- Scheduled legal balls for Innings 1 (default 120)
    inn2_scheduled_balls BIGINT NOT NULL   -- Scheduled legal balls for Innings 2 (default 120)
);

-- 4. bridge_competition_team_player: Roster mapping and player entity resolution
CREATE TABLE IF NOT EXISTS bridge_competition_team_player (
    comp_id BIGINT NOT NULL,
    comp_name VARCHAR NOT NULL,
    team_id BIGINT NOT NULL,
    team_name VARCHAR NOT NULL,
    player_id BIGINT NOT NULL,
    player_name VARCHAR NOT NULL,
    canonical_player_id BIGINT NOT NULL,   -- Resolves split entities (e.g. Basil Hameed 39444 -> 8638)
    PRIMARY KEY (comp_id, team_id, player_id)
);

-- 5. fact_playing_eleven: Match lineups, participation, roles, and Impact Player tracking
CREATE TABLE IF NOT EXISTS fact_playing_eleven (
    lineup_id VARCHAR PRIMARY KEY,         -- match_id || '_' || team_id || '_' || player_id || '_' || row_num
    match_id BIGINT NOT NULL,
    team_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    canonical_player_id BIGINT NOT NULL,
    batting_order BIGINT,
    is_played BOOLEAN NOT NULL,
    is_captain BOOLEAN,
    is_wk BOOLEAN,
    is_impact BIGINT NOT NULL,             -- 1 if substituted on as Impact Player
    is_impact_off BIGINT NOT NULL,         -- 1 if substituted off as Impact Player
    is_super_over_duplicate BOOLEAN NOT NULL -- TRUE for the 75 Super Over duplicate rows
);

-- 6. fact_delivery: Canonical delivery-level event log with verified semantics
CREATE TABLE IF NOT EXISTS fact_delivery (
    -- Original raw columns preserved verbatim
    match_id BIGINT NOT NULL,
    innings BIGINT NOT NULL,
    overid BIGINT NOT NULL,
    over_ball_num BIGINT NOT NULL,
    innings_ball_num BIGINT NOT NULL,
    batting_team_id BIGINT NOT NULL,
    bowling_team_id BIGINT NOT NULL,
    striker_id BIGINT NOT NULL,
    striker_name VARCHAR NOT NULL,
    non_striker_id BIGINT NOT NULL,
    non_striker_name VARCHAR NOT NULL,
    bowler_id BIGINT NOT NULL,
    bowler_name VARCHAR NOT NULL,
    batting_type VARCHAR NOT NULL,         -- 'RHB', 'LHB'
    bowling_type VARCHAR NOT NULL,         -- 12 granular categories
    batting_order BIGINT NOT NULL,
    runs BIGINT NOT NULL,                  -- Striker runs off bat
    is_four BOOLEAN NOT NULL,              -- Raw four flag
    is_six BOOLEAN NOT NULL,               -- Raw six flag
    is_wicket BOOLEAN NOT NULL,            -- Raw wicket flag (10,881 True)
    dismissal_type_id BIGINT,
    dismissal_type VARCHAR,
    dismissed_player_id BIGINT,
    extras_type VARCHAR NOT NULL,          -- 'None', 'wide', 'legbyes', 'Overstep', 'byes', 'other', 'Penalty'
    extras1_runs BIGINT NOT NULL,
    extras_2_runs BIGINT NOT NULL,
    pace_or_spin VARCHAR NOT NULL,         -- Raw pace/spin (contains 3 mislabeled spinners)
    bowl_speed DOUBLE NOT NULL,            -- Raw speed (contains 0.0 sentinel, -1.0, outliers > 165)
    stroke VARCHAR,
    delivery_style VARCHAR,
    over_or_around VARCHAR,
    on_or_off VARCHAR NOT NULL,
    delivery_ist_time TIMESTAMP NOT NULL,

    -- Canonical derived analytical fields (Task 02 & Task 03 verified)
    batter_runs BIGINT NOT NULL,           -- runs
    extra_runs BIGINT NOT NULL,            -- extras1_runs + extras_2_runs
    total_runs BIGINT NOT NULL,            -- runs + extras1_runs + extras_2_runs (100% verified match runs)
    is_legal_delivery BOOLEAN NOT NULL,    -- extras_type NOT IN ('wide', 'Overstep', 'other')
    is_batter_ball_faced BOOLEAN NOT NULL, -- extras_type != 'wide' (faced on no-balls/oversteps, not on wides)
    bowler_runs_conceded BIGINT NOT NULL,  -- runs + (extras1_runs + extras_2_runs) unless byes/legbyes/penalties
    is_bowler_wicket BOOLEAN NOT NULL,     -- is_wicket AND dismissal_type IN ('Caught','Bowled','LBW','Stump','Hit Wicket')
    dismissal_type_clean VARCHAR,          -- Fixes typo 'Obstracting the field' -> 'Obstructing the field'
    pace_or_spin_clean VARCHAR NOT NULL,   -- Derives pace/spin directly from bowling_type (fixes 3 bowlers)
    is_four_clean BOOLEAN NOT NULL,        -- runs = 4 (fixes 20 false-negative flags)
    is_six_clean BOOLEAN NOT NULL,         -- runs = 6 (fixes 3 false-negative flags)
    is_boundary_clean BOOLEAN NOT NULL,    -- runs IN (4, 6)
    is_dot_ball_batter BOOLEAN NOT NULL,   -- is_batter_ball_faced AND runs = 0
    is_dot_ball_bowler BOOLEAN NOT NULL,   -- is_legal_delivery AND bowler_runs_conceded = 0
    bowl_speed_valid DOUBLE,               -- Filtered physical release speed [60.0 .. 165.0]
    is_speed_missing BOOLEAN NOT NULL,     -- bowl_speed = 0.0 (38.74% missing radar sentinel)
    is_speed_outlier BOOLEAN NOT NULL,     -- bowl_speed < 0 or (bowl_speed > 0 and < 50) or bowl_speed > 165
    canonical_striker_id BIGINT NOT NULL,
    canonical_non_striker_id BIGINT NOT NULL,
    canonical_bowler_id BIGINT NOT NULL,
    canonical_dismissed_player_id BIGINT,

    PRIMARY KEY (match_id, innings, overid, over_ball_num)
);

-- Indices for rapid querying and multi-column join optimization
CREATE INDEX IF NOT EXISTS idx_dim_comp_cat ON dim_competition(competition_category);
CREATE INDEX IF NOT EXISTS idx_fact_match_comp ON fact_match(comp_id);
CREATE INDEX IF NOT EXISTS idx_fact_match_date ON fact_match(match_date);
CREATE INDEX IF NOT EXISTS idx_fact_delivery_match_inn ON fact_delivery(match_id, innings);
CREATE INDEX IF NOT EXISTS idx_fact_delivery_striker ON fact_delivery(canonical_striker_id);
CREATE INDEX IF NOT EXISTS idx_fact_delivery_bowler ON fact_delivery(canonical_bowler_id);
"""


def initialize_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Execute DDL statements to construct the analytical database schema."""
    con.execute(SCHEMA_DDL)
