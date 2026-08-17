import logging
import sqlite3
from dataclasses import dataclass
from typing import Optional, Dict, List
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
    category: str
    nationality: str


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


def _get_or_create_category(
        db_connection: sqlite3.Connection,
        competition_id: int,
        category_name: str
) -> int:
    """
    Retrieves the ID of a category, creating it if it does not exist.
    """
    cursor = db_connection.cursor()
    cursor.execute(
        "SELECT id FROM category WHERE competition_id = ? AND name = ?",
        (competition_id, category_name)
    )
    row = cursor.fetchone()

    if row:
        return row[0]

    cursor.execute(
        "INSERT INTO category (competition_id, name) VALUES (?, ?)",
        (competition_id, category_name)
    )
    db_connection.commit()
    return cursor.lastrowid


def register_competitor_manually(
        db_connection: sqlite3.Connection,
        registration: CompetitorRegistration
) -> int:
    """
    Registers a single competitor, resolving the category ID automatically.

    Args:
        db_connection: Active SQLite connection.
        registration: The competitor data structure.

    Returns:
        The ID of the inserted competitor.

    Raises:
        ValueError: If a database integrity error occurs (e.g., duplicate name).
    """
    category_id = _get_or_create_category(
        db_connection,
        registration.competition_id,
        registration.category
    )

    query = """
        INSERT INTO competitor 
        (competition_id, first_name, last_name, category_id, nationality) 
        VALUES (?, ?, ?, ?, ?)
    """
    try:
        cursor = db_connection.cursor()
        cursor.execute(
            query,
            (
                registration.competition_id,
                registration.first_name,
                registration.last_name,
                category_id,
                registration.nationality
            )
        )
        db_connection.commit()

        competitor_id = cursor.lastrowid
        logger.info(
            f"Registered competitor {registration.first_name} "
            f"{registration.last_name} ({registration.category})."
        )
        return competitor_id

    except sqlite3.IntegrityError as error:
        logger.error(f"Failed to register competitor: {error}")
        raise ValueError(
            f"Could not register competitor. {registration.first_name} "
            f"{registration.last_name} might already exist."
        )


def _find_column_index(
        headers: Dict[int, str],
        possible_names: List[str]
) -> Optional[int]:
    """Find the column index matching any of the possible names."""
    for col_idx, header_val in headers.items():
        clean_header = header_val.strip().lower()
        if any(name in clean_header for name in possible_names):
            return col_idx
    return None


def import_competitors_from_excel(
        db_connection: sqlite3.Connection,
        file_path: str,
        competition_id: int
) -> int:
    """
    Reads an Excel file and registers multiple competitors.
    Smartly finds columns based on keywords (Name, Category, Nationality).

    Args:
        db_connection: Active SQLite connection.
        file_path: Path to the .xlsx file.
        competition_id: The ID of the target competition.

    Returns:
        The number of successfully imported competitors.

    Raises:
        FileNotFoundError: If the Excel file does not exist.
        ValueError: If the file format is invalid or data is corrupted.
        KeyError: If mandatory columns are not found.
    """
    try:
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook.active
    except FileNotFoundError:
        logger.error(f"Excel file not found at {file_path}.")
        raise FileNotFoundError(f"Cannot locate file: {file_path}")
    except Exception as error:
        logger.error(f"Invalid Excel file format: {error}")
        raise ValueError("The provided file is not a valid Excel document.")

    if sheet is None:
        raise ValueError("Excel file is empty.")

    # 1. Identify columns
    headers: Dict[int, str] = {}
    for col_idx, cell in enumerate(sheet[1], start=1):
        if cell.value:
            headers[col_idx] = str(cell.value)

    first_name_idx = _find_column_index(headers, ["first", "prenom", "prénom", "name"])
    last_name_idx = _find_column_index(headers, ["last", "nom", "family"])
    category_idx = _find_column_index(headers, ["cat", "division"])
    nationality_idx = _find_column_index(headers, ["nat", "country", "pays"])

    if not first_name_idx or not last_name_idx:
        raise KeyError("Could not find required 'First Name' and 'Last Name' columns in Excel.")

    imported_count = 0

    # 2. Process rows
    for row_index in range(2, sheet.max_row + 1):
        first_name = sheet.cell(row=row_index, column=first_name_idx).value
        last_name = sheet.cell(row=row_index, column=last_name_idx).value

        if not first_name or not last_name:
            continue

        category_val = "Open Boy"
        if category_idx and sheet.cell(row=row_index, column=category_idx).value:
            category_val = str(sheet.cell(row=row_index, column=category_idx).value).strip()

        nationality_val = "FRA"
        if nationality_idx and sheet.cell(row=row_index, column=nationality_idx).value:
            nationality_val = str(sheet.cell(row=row_index, column=nationality_idx).value).strip()

        registration = CompetitorRegistration(
            competition_id=competition_id,
            first_name=str(first_name).strip(),
            last_name=str(last_name).strip(),
            category=category_val,
            nationality=nationality_val.upper()
        )

        try:
            register_competitor_manually(db_connection, registration)
            imported_count += 1
        except ValueError as error:
            logger.warning(f"Skipping row {row_index} due to data conflict: {error}")

    logger.info(f"Successfully imported {imported_count} competitors.")
    return imported_count
