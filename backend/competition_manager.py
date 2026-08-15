import logging
import sqlite3
from dataclasses import dataclass
from typing import Optional, List
import openpyxl

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Competition:
    """
    Data structure representing a competition event.
    """
    name: str
    event_date: str
    id: Optional[int] = None


@dataclass
class CompetitorRegistration:
    """
    Data structure representing a competitor to be registered.
    """
    competition_id: int
    first_name: str
    last_name: str
    bib_number: int


def create_competition(
        db_connection: sqlite3.Connection,
        competition_name: str,
        date_str: str
) -> int:
    """
    Creates a new competition in the database.

    Args:
        db_connection: Active SQLite connection.
        competition_name: The name of the event.
        date_str: Date of the event (e.g., YYYY-MM-DD).

    Returns:
        The ID of the newly created competition.
    """
    query = "INSERT INTO competition (name, event_date) VALUES (?, ?)"
    cursor = db_connection.cursor()
    cursor.execute(query, (competition_name, date_str))
    db_connection.commit()

    competition_id = cursor.lastrowid
    logger.info(
        f"Created competition '{competition_name}' "
        f"with ID {competition_id}."
    )
    return competition_id


def register_competitor_manually(
        db_connection: sqlite3.Connection,
        registration: CompetitorRegistration
) -> int:
    """
    Registers a single competitor, typically from a web form.

    Args:
        db_connection: Active SQLite connection.
        registration: The competitor data structure.

    Returns:
        The ID of the inserted competitor.

    Raises:
        ValueError: If a database integrity error occurs (e.g., duplicate bib).
    """
    query = """
        INSERT INTO competitor 
        (competition_id, first_name, last_name, bib_number) 
        VALUES (?, ?, ?, ?)
    """
    try:
        cursor = db_connection.cursor()
        cursor.execute(
            query,
            (
                registration.competition_id,
                registration.first_name,
                registration.last_name,
                registration.bib_number
            )
        )
        db_connection.commit()

        competitor_id = cursor.lastrowid
        logger.info(
            f"Registered competitor {registration.first_name} "
            f"{registration.last_name} (Bib: {registration.bib_number})."
        )
        return competitor_id

    except sqlite3.IntegrityError as error:
        logger.error(f"Failed to register competitor: {error}")
        raise ValueError(
            f"Could not register competitor. Bib number "
            f"{registration.bib_number} might already exist."
        )


def import_competitors_from_excel(
        db_connection: sqlite3.Connection,
        file_path: str,
        competition_id: int
) -> int:
    """
    Reads an Excel file and registers multiple competitors.
    Expects columns: FirstName, LastName, BibNumber.

    Args:
        db_connection: Active SQLite connection.
        file_path: Path to the .xlsx file.
        competition_id: The ID of the target competition.

    Returns:
        The number of successfully imported competitors.

    Raises:
        FileNotFoundError: If the Excel file does not exist.
        ValueError: If the file format is invalid or data is corrupted.
    """
    try:
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook.active
    except FileNotFoundError:
        logger.error(f"Excel file not found at {file_path}.")
        raise FileNotFoundError(f"Cannot locate file: {file_path}")
    except Exception as error:
        # Note: openpyxl raises BadZipFile if not a valid xlsx
        logger.error(f"Invalid Excel file format: {error}")
        raise ValueError("The provided file is not a valid Excel document.")

    imported_count = 0

    # Assuming row 1 is headers, we start at row 2
    for row_index in range(2, sheet.max_row + 1):
        first_name = sheet.cell(row=row_index, column=1).value
        last_name = sheet.cell(row=row_index, column=2).value
        bib_number = sheet.cell(row=row_index, column=3).value

        if not first_name or not last_name or not bib_number:
            continue  # Skip incomplete rows

        registration = CompetitorRegistration(
            competition_id=competition_id,
            first_name=str(first_name),
            last_name=str(last_name),
            bib_number=int(bib_number)
        )

        try:
            register_competitor_manually(db_connection, registration)
            imported_count += 1
        except ValueError as error:
            logger.warning(
                f"Skipping row {row_index} due to data conflict: {error}"
            )

    logger.info(f"Successfully imported {imported_count} competitors.")
    return imported_count
