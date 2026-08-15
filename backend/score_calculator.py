import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
VALID_JUDGE_COUNTS: Tuple[int, int] = (3, 5)
SCORES_TO_KEEP: int = 3
ROUNDING_PRECISION: int = 3


@dataclass
class RunScore:
    """
    Data structure representing a competitor's run and its scores.
    """
    competitor_id: int
    run_number: int
    raw_scores: List[float]
    final_score: Optional[float] = None


def calculate_average_score(scores: List[float]) -> float:
    """
    Calculates the final average score based on the competition rules.

    If 3 scores are provided, averages all of them.
    If 5 scores are provided, drops the highest and lowest scores,
    and averages the 3 remaining median scores.

    Args:
        scores: A list of raw scores given by the judges.

    Returns:
        The computed final score rounded to the specified precision.

    Raises:
        ValueError: If the amount of scores is not exactly 3 or 5.
    """
    score_count = len(scores)

    if score_count not in VALID_JUDGE_COUNTS:
        logger.error(
            f"Invalid score count: {score_count}. "
            f"Expected {VALID_JUDGE_COUNTS}."
        )
        raise ValueError(
            f"Cannot calculate score: expected 3 or 5 scores, "
            f"but got {score_count}."
        )

    if score_count == 3:
        final_score = sum(scores) / float(SCORES_TO_KEEP)
        logger.info(
            f"Calculated score for 3 judges: "
            f"{final_score:.{ROUNDING_PRECISION}f}"
        )
        return round(final_score, ROUNDING_PRECISION)

    # Logic for 5 judges
    sorted_scores = sorted(scores)

    # Drop lowest (index 0) and highest (last index), keep the middle 3
    median_scores = sorted_scores[1:4]
    final_score = sum(median_scores) / float(SCORES_TO_KEEP)

    logger.info(
        f"Calculated score for 5 judges. Dropped {sorted_scores[0]} "
        f"and {sorted_scores[-1]}. Final: "
        f"{final_score:.{ROUNDING_PRECISION}f}"
    )

    return round(final_score, ROUNDING_PRECISION)


def process_run(
    competitor_id: int,
    run_number: int,
    scores: List[float]
) -> RunScore:
    """
    Processes the raw scores and returns a complete RunScore object.

    Args:
        competitor_id: The unique identifier of the competitor.
        run_number: The sequential number of the run (1, 2, or 3).
        scores: The raw scores submitted by the judges.

    Returns:
        A RunScore instance populated with raw data and the final score.
    """
    final_score = calculate_average_score(scores)

    run_result = RunScore(
        competitor_id=competitor_id,
        run_number=run_number,
        raw_scores=scores,
        final_score=final_score
    )

    return run_result
