"""
RR ScoutIQ — Delivery Context & Match-State Reconstruction Test Suite
Deterministic unit tests covering all 14 required edge cases and mathematical formulations:
1. Normal legal delivery
2. Wide delivery
3. No-ball / Overstep
4. Bye and leg-bye
5. Batter dismissal
6. Run-out
7. Over boundary
8. Innings transition
9. Chase-state calculation
10. Shortened innings
11. Revised target handling
12. Pre-delivery state vs post-delivery state
13. Duplicate delivery detection
14. Missing match relationships
"""

from __future__ import annotations
import duckdb
import pytest

from src.ingestion.database import initialize_schema
from src.preprocessing.delivery_context import (
    create_delivery_context_view,
    validate_delivery_context,
)


@pytest.fixture
def test_db():
    """Build in-memory DuckDB database with schema and deterministic test fixtures."""
    con = duckdb.connect(":memory:")
    initialize_schema(con)

    # 1. Base Competitions
    con.execute("""
        INSERT INTO dim_competition VALUES
        (101, 'IPL 2024', 'T20', '2024', 'IPL', TRUE),
        (102, 'T20I Bilateral', 'T20I', '2024', 'T20I', TRUE)
    """)

    # 2. Base Teams
    con.execute("""
        INSERT INTO dim_team VALUES
        (101, 1, 'Team Alpha'),
        (101, 2, 'Team Beta'),
        (102, 10, 'Team Gamma'),
        (102, 20, 'Team Delta')
    """)

    # 3. Base Matches
    # Match 1: Full 20-over match (innings 1: 150 runs, innings 2: chase 151)
    # Match 2: Shortened 10-over match (scheduled 60 balls, revised target 85)
    con.execute("""
        INSERT INTO fact_match (
            match_id, comp_id, match_number, match_date, stage, venue_id,
            venue_country, home_team_id, home_team, away_team_id, away_team,
            man_of_the_match_raw, knock_out, is_playoff, win_team_id, result,
            match_status, has_delivery_data, is_shortened_match,
            inn1_scheduled_balls, inn2_scheduled_balls, revised_target
        ) VALUES
        (1001, 101, 1, '2024-04-01', 'League', 1, 'India', 1, 'Team Alpha', 2, 'Team Beta', 1, 0, FALSE, 2, 'Team Beta Won by 5 wickets', 'Completed', TRUE, FALSE, 120, 120, NULL),
        (1002, 102, 2, '2024-04-02', 'League', 2, 'India', 10, 'Team Gamma', 20, 'Team Delta', 2, 0, FALSE, 20, 'Team Delta Won (DLS)', 'Completed', TRUE, TRUE, 60, 60, 85)
    """)

    yield con
    con.close()


def insert_test_delivery(
    con: duckdb.DuckDBPyConnection,
    match_id: int,
    innings: int,
    overid: int,
    over_ball_num: int,
    innings_ball_num: int,
    runs: int = 0,
    extras_type: str = "None",
    extras1_runs: int = 0,
    extras_2_runs: int = 0,
    is_wicket: bool = False,
    dismissal_type: str | None = None,
    striker_id: int = 101,
    non_striker_id: int = 102,
    bowler_id: int = 201,
    bowling_type: str = "Right-arm Fast",
    bowl_speed: float = 135.0,
):
    """Helper to insert a single canonical delivery into fact_delivery with derived columns."""
    extra_runs = extras1_runs + extras_2_runs
    total_runs = runs + extra_runs
    is_legal = extras_type not in ("wide", "Overstep", "other")
    is_faced = extras_type != "wide"
    bowler_runs = runs + (extra_runs if extras_type not in ("byes", "legbyes", "Penalty") else 0)
    is_bowler_wkt = is_wicket and dismissal_type in ("Caught", "Bowled", "LBW", "Stump", "Hit Wicket")
    is_four = (runs == 4)
    is_six = (runs == 6)
    is_boundary = runs in (4, 6)
    is_dot_bat = is_faced and (runs == 0)
    is_dot_bowl = is_legal and (bowler_runs == 0)
    valid_speed = bowl_speed if (60.0 <= bowl_speed <= 165.0) else None
    speed_missing = (bowl_speed == 0.0)
    speed_outlier = (bowl_speed < 0.0 or (0.0 < bowl_speed < 50.0) or bowl_speed > 165.0)
    pace_spin = "Spin" if bowling_type in ("Right-arm offbreak", "Slow left-arm orthodox", "Right-arm Leg-Break", "Left-arm Chinaman") else "Pace"

    con.execute("""
        INSERT INTO fact_delivery (
            match_id, innings, overid, over_ball_num, innings_ball_num,
            batting_team_id, bowling_team_id, striker_id, striker_name,
            non_striker_id, non_striker_name, bowler_id, bowler_name,
            batting_type, bowling_type, batting_order, runs, is_four,
            is_six, is_wicket, dismissal_type_id, dismissal_type,
            dismissed_player_id, extras_type, extras1_runs, extras_2_runs,
            pace_or_spin, bowl_speed, stroke, delivery_style,
            over_or_around, on_or_off, delivery_ist_time,
            batter_runs, extra_runs, total_runs, is_legal_delivery,
            is_batter_ball_faced, bowler_runs_conceded, is_bowler_wicket,
            dismissal_type_clean, pace_or_spin_clean, is_four_clean,
            is_six_clean, is_boundary_clean, is_dot_ball_batter,
            is_dot_ball_bowler, bowl_speed_valid, is_speed_missing,
            is_speed_outlier, canonical_striker_id, canonical_non_striker_id,
            canonical_bowler_id, canonical_dismissed_player_id
        ) VALUES (
            ?, ?, ?, ?, ?,
            1, 2, ?, 'Striker',
            ?, 'NonStriker', ?, 'Bowler',
            'RHB', ?, 1, ?, ?,
            ?, ?, 1, ?,
            ?, ?, ?, ?,
            ?, ?, 'Drive', 'Seam',
            'Over', 'Off-side', '2024-04-01 19:30:00',
            ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?
        )
    """, [
        match_id, innings, overid, over_ball_num, innings_ball_num,
        striker_id, non_striker_id, bowler_id, bowling_type, runs, is_four,
        is_six, is_wicket, dismissal_type, striker_id if is_wicket else None,
        extras_type, extras1_runs, extras_2_runs, pace_spin, bowl_speed,
        runs, extra_runs, total_runs, is_legal,
        is_faced, bowler_runs, is_bowler_wkt,
        dismissal_type, pace_spin, is_four,
        is_six, is_boundary, is_dot_bat,
        is_dot_bowl, valid_speed, speed_missing,
        speed_outlier, striker_id, non_striker_id,
        bowler_id, striker_id if is_wicket else None
    ])


class TestDeliveryContextCases:
    """Rigorous verification of match-state reconstruction across all 14 required cases."""

    def test_case_01_normal_legal_delivery(self, test_db):
        """Case 1: Normal legal delivery scores runs off the bat, advances legal balls and runs."""
        insert_test_delivery(test_db, 1001, 1, 1, 1, 1, runs=1)
        insert_test_delivery(test_db, 1001, 1, 1, 2, 2, runs=4)

        create_delivery_context_view(test_db)
        rows = test_db.execute("SELECT innings_ball_num, pre_delivery_runs, pre_delivery_legal_balls, total_runs, is_legal_delivery FROM fact_delivery_context WHERE match_id = 1001 ORDER BY innings_ball_num").fetchall()

        # Ball 1 pre-state: 0 runs, 0 legal balls
        assert rows[0] == (1, 0, 0, 1, True)
        # Ball 2 pre-state: 1 run, 1 legal ball
        assert rows[1] == (2, 1, 1, 4, True)

    def test_case_02_wide_delivery(self, test_db):
        """Case 2: Wide delivery is re-bowled (not legal), not faced by batter, conceded by bowler."""
        insert_test_delivery(test_db, 1001, 1, 1, 1, 1, runs=0, extras_type="wide", extras1_runs=1)
        insert_test_delivery(test_db, 1001, 1, 1, 2, 2, runs=0)

        create_delivery_context_view(test_db)
        d1 = test_db.execute("SELECT total_runs, is_legal_delivery, is_batter_ball_faced, bowler_runs_conceded, pre_delivery_legal_balls FROM fact_delivery_context WHERE match_id = 1001 AND innings_ball_num = 1").fetchone()
        assert d1 == (1, False, False, 1, 0)

        # Ball 2 pre-state: 1 run conceded, but STILL 0 legal balls bowled!
        d2 = test_db.execute("SELECT pre_delivery_runs, pre_delivery_legal_balls, legal_balls_remaining FROM fact_delivery_context WHERE match_id = 1001 AND innings_ball_num = 2").fetchone()
        assert d2 == (1, 0, 120)

    def test_case_03_no_ball(self, test_db):
        """Case 3: No-ball (Overstep) is not legal, faced by batter, extra run + off bat runs."""
        insert_test_delivery(test_db, 1001, 1, 1, 1, 1, runs=2, extras_type="Overstep", extras1_runs=1)
        insert_test_delivery(test_db, 1001, 1, 1, 2, 2, runs=1)

        create_delivery_context_view(test_db)
        d1 = test_db.execute("SELECT total_runs, batter_runs, is_legal_delivery, is_batter_ball_faced, bowler_runs_conceded FROM fact_delivery_context WHERE match_id = 1001 AND innings_ball_num = 1").fetchone()
        assert d1 == (3, 2, False, True, 3)

        # Pre-state of ball 2: 3 runs, 0 legal balls
        d2 = test_db.execute("SELECT pre_delivery_runs, pre_delivery_legal_balls FROM fact_delivery_context WHERE match_id = 1001 AND innings_ball_num = 2").fetchone()
        assert d2 == (3, 0)

    def test_case_04_bye_and_leg_bye(self, test_db):
        """Case 4: Byes and leg-byes count as legal deliveries, but are NOT charged to bowler."""
        insert_test_delivery(test_db, 1001, 1, 1, 1, 1, runs=0, extras_type="legbyes", extras1_runs=2)
        insert_test_delivery(test_db, 1001, 1, 1, 2, 2, runs=0, extras_type="byes", extras1_runs=1)

        create_delivery_context_view(test_db)
        rows = test_db.execute("SELECT total_runs, is_legal_delivery, bowler_runs_conceded FROM fact_delivery_context WHERE match_id = 1001 ORDER BY innings_ball_num").fetchall()
        assert rows[0] == (2, True, 0)  # 2 team runs, legal, 0 runs to bowler
        assert rows[1] == (1, True, 0)  # 1 team run, legal, 0 runs to bowler

    def test_case_05_batter_dismissal(self, test_db):
        """Case 5: Bowler dismissal increments wickets, decrements wickets in hand."""
        insert_test_delivery(test_db, 1001, 1, 1, 1, 1, runs=0, is_wicket=True, dismissal_type="Bowled")
        insert_test_delivery(test_db, 1001, 1, 1, 2, 2, runs=1)

        create_delivery_context_view(test_db)
        d1 = test_db.execute("SELECT is_bowler_wicket, pre_delivery_wickets, wickets_in_hand, post_delivery_wickets FROM fact_delivery_context WHERE match_id = 1001 AND innings_ball_num = 1").fetchone()
        assert d1 == (True, 0, 10, 1)

        d2 = test_db.execute("SELECT pre_delivery_wickets, wickets_in_hand FROM fact_delivery_context WHERE match_id = 1001 AND innings_ball_num = 2").fetchone()
        assert d2 == (1, 9)

    def test_case_06_run_out(self, test_db):
        """Case 6: Run-out increments team wickets, but is NOT credited as a bowler wicket."""
        insert_test_delivery(test_db, 1001, 1, 1, 1, 1, runs=1, is_wicket=True, dismissal_type="RunOut")

        create_delivery_context_view(test_db)
        d1 = test_db.execute("SELECT is_wicket, is_bowler_wicket, post_delivery_wickets FROM fact_delivery_context WHERE match_id = 1001 AND innings_ball_num = 1").fetchone()
        assert d1 == (True, False, 1)  # is_wicket=True, but is_bowler_wicket=False!

    def test_case_07_over_boundary(self, test_db):
        """Case 7: Completing 6 legal deliveries increments completed_overs and advances overid."""
        for b in range(1, 7):
            insert_test_delivery(test_db, 1001, 1, 1, b, b, runs=1)
        insert_test_delivery(test_db, 1001, 1, 2, 1, 7, runs=2)

        create_delivery_context_view(test_db)
        # Ball 6 in over 1
        b6 = test_db.execute("SELECT overid, pre_delivery_legal_balls, completed_overs, balls_in_current_over FROM fact_delivery_context WHERE match_id = 1001 AND innings_ball_num = 6").fetchone()
        assert b6 == (1, 5, 0, 5)

        # Ball 1 in over 2 (7th ball overall)
        b7 = test_db.execute("SELECT overid, pre_delivery_legal_balls, completed_overs, balls_in_current_over FROM fact_delivery_context WHERE match_id = 1001 AND innings_ball_num = 7").fetchone()
        assert b7 == (2, 6, 1, 0)

    def test_case_08_innings_transition(self, test_db):
        """Case 8: Pre-delivery states completely reset across innings transition (zero leakage)."""
        # Innings 1: 2 balls, scores 10 runs
        insert_test_delivery(test_db, 1001, 1, 1, 1, 1, runs=6)
        insert_test_delivery(test_db, 1001, 1, 1, 2, 2, runs=4)

        # Innings 2: Ball 1 starts chase
        insert_test_delivery(test_db, 1001, 2, 1, 1, 1, runs=1)

        create_delivery_context_view(test_db)
        i2_b1 = test_db.execute("""
            SELECT innings, pre_delivery_runs, pre_delivery_wickets, pre_delivery_legal_balls,
                   target_runs, is_chase, runs_required, required_run_rate
            FROM fact_delivery_context
            WHERE match_id = 1001 AND innings = 2 AND innings_ball_num = 1
        """).fetchone()

        # Pre-delivery state in Innings 2 is fresh (0 runs, 0 wkts, 0 legal balls)
        assert i2_b1[0] == 2
        assert i2_b1[1] == 0  # pre_delivery_runs
        assert i2_b1[2] == 0  # pre_delivery_wickets
        assert i2_b1[3] == 0  # pre_delivery_legal_balls
        assert i2_b1[4] == 11 # target_runs: 10 + 1 = 11
        assert i2_b1[5] is True # is_chase
        assert i2_b1[6] == 11 # runs_required
        assert i2_b1[7] == 0.55 # RRR = (11 * 6) / 120 = 0.55

    def test_case_09_chase_state_calculation(self, test_db):
        """Case 9: Chase calculations (target, runs required, RRR, CRR) update each delivery."""
        insert_test_delivery(test_db, 1001, 1, 1, 1, 1, runs=6)
        insert_test_delivery(test_db, 1001, 1, 1, 2, 2, runs=6) # Inn 1 total = 12 -> Target = 13

        insert_test_delivery(test_db, 1001, 2, 1, 1, 1, runs=4) # Chase ball 1
        insert_test_delivery(test_db, 1001, 2, 1, 2, 2, runs=0) # Chase ball 2

        create_delivery_context_view(test_db)
        # Ball 1: pre runs = 0, req = 13, RRR = (13*6)/120 = 0.65, CRR = 0.0
        c1 = test_db.execute("SELECT pre_delivery_runs, runs_required, required_run_rate, current_run_rate FROM fact_delivery_context WHERE match_id = 1001 AND innings = 2 AND innings_ball_num = 1").fetchone()
        assert c1 == (0, 13, 0.65, 0.0)

        # Ball 2: pre runs = 4, req = 9, RRR = (9*6)/119 = 0.4538, CRR = (4*6)/1 = 24.0
        c2 = test_db.execute("SELECT pre_delivery_runs, runs_required, required_run_rate, current_run_rate FROM fact_delivery_context WHERE match_id = 1001 AND innings = 2 AND innings_ball_num = 2").fetchone()
        assert c2 == (4, 9, 0.4538, 24.0)

    def test_case_10_shortened_innings(self, test_db):
        """Case 10: Shortened matches compute balls remaining from scheduled limit (e.g. 60 balls)."""
        # Match 1002 has inn1_scheduled_balls = 60, inn2_scheduled_balls = 60, revised_target = 85
        insert_test_delivery(test_db, 1002, 1, 1, 1, 1, runs=1)

        create_delivery_context_view(test_db)
        s1 = test_db.execute("SELECT scheduled_legal_balls, legal_balls_remaining, is_shortened_match, innings_phase FROM fact_delivery_context WHERE match_id = 1002").fetchone()
        assert s1 == (60, 60, True, "Powerplay")

    def test_case_11_revised_target_handling(self, test_db):
        """Case 11: DLS matches compute runs required using revised_target directly."""
        # Match 1002 has revised_target = 85, scheduled 60 balls
        insert_test_delivery(test_db, 1002, 2, 1, 1, 1, runs=0)
        insert_test_delivery(test_db, 1002, 2, 1, 2, 2, runs=6)

        create_delivery_context_view(test_db)
        d1 = test_db.execute("SELECT target_runs, runs_required, required_run_rate FROM fact_delivery_context WHERE match_id = 1002 AND innings_ball_num = 1").fetchone()
        assert d1 == (85, 85, 8.5) # RRR = (85 * 6) / 60 = 8.5

        d2 = test_db.execute("SELECT pre_delivery_runs, runs_required, required_run_rate FROM fact_delivery_context WHERE match_id = 1002 AND innings_ball_num = 2").fetchone()
        # After 0 runs on ball 1: runs_req = 85, balls_rem = 59 -> RRR = (85 * 6) / 59 = 8.6441
        assert d2 == (0, 85, 8.6441)

    def test_case_12_pre_vs_post_delivery_state(self, test_db):
        """Case 12: Pre-delivery state of ball N+1 matches post-delivery state of ball N exactly."""
        insert_test_delivery(test_db, 1001, 1, 1, 1, 1, runs=4, is_wicket=False)
        insert_test_delivery(test_db, 1001, 1, 1, 2, 2, runs=1, is_wicket=True, dismissal_type="Caught")
        insert_test_delivery(test_db, 1001, 1, 1, 3, 3, runs=0)

        create_delivery_context_view(test_db)
        rows = test_db.execute("""
            SELECT innings_ball_num, pre_delivery_runs, post_delivery_runs,
                   pre_delivery_wickets, post_delivery_wickets,
                   pre_delivery_legal_balls, post_delivery_legal_balls
            FROM fact_delivery_context
            WHERE match_id = 1001
            ORDER BY innings_ball_num
        """).fetchall()

        # Ball 1 post matches Ball 2 pre
        assert rows[0][2] == rows[1][1] # post runs ball 1 == pre runs ball 2
        assert rows[0][4] == rows[1][3] # post wkts ball 1 == pre wkts ball 2
        assert rows[0][6] == rows[1][5] # post legal balls ball 1 == pre legal balls ball 2

        # Ball 2 post matches Ball 3 pre
        assert rows[1][2] == rows[2][1]
        assert rows[1][4] == rows[2][3]
        assert rows[1][6] == rows[2][5]

    def test_case_13_duplicate_delivery_detection(self, test_db):
        """Case 13: Delivery primary key rejects duplicate (match_id, innings, overid, over_ball_num)."""
        insert_test_delivery(test_db, 1001, 1, 1, 1, 1, runs=1)
        with pytest.raises(Exception):
            insert_test_delivery(test_db, 1001, 1, 1, 1, 2, runs=2)

    def test_case_14_missing_match_relationships(self, test_db):
        """Case 14: Automated validation detects deliveries referencing missing matches."""
        # Insert a delivery with non-existent match_id = 9999
        con_bad = duckdb.connect(":memory:")
        initialize_schema(con_bad)
        insert_test_delivery(con_bad, 9999, 1, 1, 1, 1, runs=1)

        val = validate_delivery_context(con_bad)
        # Because fact_delivery has 1 row and fact_match has 0 rows, inner join in context view yields 0 rows!
        # row_count_match check will fail!
        assert val["row_count_match"][0] is False
        assert val["all_passed"] is False
        con_bad.close()

    def test_case_15_unrecorded_dls_target_handling(self, test_db):
        """Case 15: Match 23674 has unrecorded DLS target; chase target & RRR must be set to NULL."""
        # Insert Match 23674 with DLS in result and NULL revised_target
        test_db.execute("""
            INSERT INTO fact_match (
                match_id, comp_id, match_number, match_date, stage, venue_id,
                venue_country, home_team_id, home_team, away_team_id, away_team,
                man_of_the_match_raw, knock_out, is_playoff, win_team_id, result,
                match_status, has_delivery_data, is_shortened_match,
                inn1_scheduled_balls, inn2_scheduled_balls, revised_target
            ) VALUES
            (23674, 102, 1, '2023-03-27', 'League', 5, 'Bangladesh', 10, 'Team Gamma', 20, 'Team Delta', 1, 0, FALSE, 10, 'Bangladesh Won by 6 Wickets(D/L Method)', 'Completed', TRUE, TRUE, 102, 102, NULL)
        """)

        # Innings 1: 1 ball, 6 runs
        insert_test_delivery(test_db, 23674, 1, 1, 1, 1, runs=6)
        # Innings 2: 1 ball, 1 run
        insert_test_delivery(test_db, 23674, 2, 1, 1, 1, runs=1)

        create_delivery_context_view(test_db)
        d = test_db.execute("""
            SELECT match_id, innings, target_runs, runs_required, required_run_rate, is_chase
            FROM fact_delivery_context
            WHERE match_id = 23674 AND innings = 2
        """).fetchone()

        assert d[0] == 23674
        assert d[1] == 2
        # Target must NOT be fabricated as 6 + 1 = 7; it must be NULL (unavailable)
        assert d[2] is None
        assert d[3] is None
        assert d[4] is None
        assert d[5] is True
