import logging
import os
from typing import List

from db_manager import setup_database, get_connection
from competition_manager import (
    create_competition,
    register_competitor_manually,
    CompetitorRegistration
)
from score_calculator import process_run, ROUNDING_PRECISION

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEST_DB: str = "test_contest.db"


def run_integration_test() -> None:
    """
    Runs a full integration test on the backend core modules.
    Ensures DB creation, registration, and math logic work together.
    """
    # Clean up previous test database if it exists
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    logger.info("--- 1. Testing Database Setup ---")
    setup_database(TEST_DB)

    with get_connection(TEST_DB) as connection:
        logger.info("--- 2. Testing Competition Creation ---")
        comp_id = create_competition(
            connection,
            competition_name="Summer Jam 2026",
            date_str="2026-08-14"
        )

        logger.info("--- 3. Testing Competitor Registration ---")
        skater = CompetitorRegistration(
            competition_id=comp_id,
            first_name="Tony",
            last_name="Hawk",
            bib_number=42
        )
        skater_id = register_competitor_manually(connection, skater)

        logger.info("--- 4. Testing Score Calculation (5 Judges) ---")
        # With 5 judges: lowest (7.0) and highest (9.5) are dropped.
        # Remaining: 8.5, 8.8, 9.0. Average: 8.77
        logger.info("--- 4. Testing Score Calculation (5 Judges) ---")

        raw_scores: List[float] = [8.5, 9.0, 7.0, 8.8, 9.5]
        result = process_run(skater_id, run_number=1, scores=raw_scores)

        # Calculate the expected score dynamically using the constant
        # Dropped: 7.0, 9.5. Kept: 8.5, 8.8, 9.0. Sum = 26.3
        expected_raw_score = (8.5 + 8.8 + 9.0) / 3.0
        expected_score = round(expected_raw_score, ROUNDING_PRECISION)

        if result.final_score == expected_score:
            logger.info(
                f"SUCCESS! Final score is correct: "
                f"{result.final_score:.{ROUNDING_PRECISION}f}"
            )
        else:
            logger.error(
                f"FAIL! Expected "
                f"{expected_score:.{ROUNDING_PRECISION}f}, "
                f"got {result.final_score:.{ROUNDING_PRECISION}f}"
            )


if __name__ == "__main__":
    run_integration_test()
