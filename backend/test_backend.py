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
    Ensures DB creation, registration with new identity fields,
    math logic on a 0-100 scale, and error handling work together.
    """
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    logger.info("--- 1. Testing Database Setup ---")
    setup_database(TEST_DB)

    with get_connection(TEST_DB) as connection:
        logger.info("--- 2. Testing Competition Creation ---")
        comp_id: int = create_competition(
            connection,
            competition_name="Summer Jam 2026",
            date_str="2026-08-14"
        )

        logger.info("--- 3. Testing Competitor Registration ---")
        skater = CompetitorRegistration(
            competition_id=comp_id,
            first_name="Tony",
            last_name="Hawk",
            category="Open Boy",
            nationality="USA"
        )
        skater_id: int = register_competitor_manually(connection, skater)

        logger.info("--- 4. Testing Score Calculation (5 Judges - Scale 0-100) ---")
        raw_scores_five: List[float] = [85.0, 90.0, 70.0, 88.0, 95.0]
        result_five = process_run(skater_id, run_number=1, scores=raw_scores_five)

        # Dropped: 70.0, 95.0. Kept: 85.0, 88.0, 90.0.
        expected_raw_score_five: float = (85.0 + 88.0 + 90.0) / 3.0
        expected_score_five: float = round(expected_raw_score_five, ROUNDING_PRECISION)

        if result_five.final_score == expected_score_five:
            logger.info(
                f"SUCCESS! 5 Judges final score is correct: "
                f"{result_five.final_score:.{ROUNDING_PRECISION}f}"
            )
        else:
            logger.error(
                f"FAIL! Expected "
                f"{expected_score_five:.{ROUNDING_PRECISION}f}, "
                f"got {result_five.final_score:.{ROUNDING_PRECISION}f}"
            )

        logger.info("--- 5. Testing Score Calculation (3 Judges - No Drop) ---")
        raw_scores_three: List[float] = [85.0, 90.0, 88.0]
        result_three = process_run(skater_id, run_number=2, scores=raw_scores_three)

        expected_raw_score_three: float = (85.0 + 90.0 + 88.0) / 3.0
        expected_score_three: float = round(expected_raw_score_three, ROUNDING_PRECISION)

        if result_three.final_score == expected_score_three:
            logger.info(
                f"SUCCESS! 3 Judges final score is correct: "
                f"{result_three.final_score:.{ROUNDING_PRECISION}f}"
            )
        else:
            logger.error(
                f"FAIL! Expected "
                f"{expected_score_three:.{ROUNDING_PRECISION}f}, "
                f"got {result_three.final_score:.{ROUNDING_PRECISION}f}"
            )

        logger.info("--- 6. Testing Exception Handling (Empty Scores) ---")
        try:
            invalid_scores: List[float] = []
            process_run(skater_id, run_number=3, scores=invalid_scores)
            logger.error("FAIL! Should have raised ValueError for empty scores.")
        except ValueError as e:
            logger.info(f"SUCCESS! Caught expected ValueError: {e}")


if __name__ == "__main__":
    run_integration_test()
