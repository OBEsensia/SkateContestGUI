import logging
import sqlite3
from dataclasses import dataclass
from typing import Optional, Dict, List, Any
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Competition:
    """Data structure representing a competition event."""
    name: str
    event_date: str
    id: Optional[int] = None


@dataclass
class CompetitorRegistration:
    """Data structure representing a competitor to be registered."""
    competition_id: int
    first_name: str
    last_name: str
    category: str
    nationality: str


@dataclass
class PoolCreateData:
    """Data structure for creating a new pool/heat."""
    competition_id: int
    category_id: int
    phase: str
    name: str


def create_competition(
        db_connection: sqlite3.Connection,
        competition_name: str,
        date_str: str
) -> int:
    query = "INSERT INTO competition (name, event_date) VALUES (?, ?)"
    cursor = db_connection.cursor()
    cursor.execute(query, (competition_name, date_str))
    db_connection.commit()

    competition_id = cursor.lastrowid
    logger.info(f"Created competition '{competition_name}' with ID {competition_id}.")
    return competition_id


def _get_or_create_category(
        db_connection: sqlite3.Connection,
        competition_id: int,
        category_name: str
) -> int:
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
    """Smartly finds the column index, avoiding 'nom'/'prénom' collisions."""
    for col_idx, header_val in headers.items():
        clean_header = header_val.strip().lower()
        if clean_header in possible_names:
            return col_idx

    for col_idx, header_val in headers.items():
        clean_header = header_val.strip().lower()
        for name in possible_names:
            if name == "nom" and ("pre" in clean_header or "pré" in clean_header):
                continue
            if name in clean_header:
                return col_idx
    return None


def import_competitors_from_excel(
        db_connection: sqlite3.Connection,
        file_path: str,
        competition_id: int
) -> int:
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


def create_pool(
        db_connection: sqlite3.Connection,
        pool_data: PoolCreateData
) -> int:
    query = """
        INSERT INTO pool (competition_id, category_id, phase, name)
        VALUES (?, ?, ?, ?)
    """
    try:
        cursor = db_connection.cursor()
        cursor.execute(
            query,
            (
                pool_data.competition_id,
                pool_data.category_id,
                pool_data.phase,
                pool_data.name
            )
        )
        db_connection.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError(f"Pool '{pool_data.name}' already exists for this phase.")


def assign_competitor_to_pool(
        db_connection: sqlite3.Connection,
        pool_id: int,
        competitor_id: int,
        start_order: int
) -> None:
    query = """
        INSERT OR REPLACE INTO pool_competitor (pool_id, competitor_id, start_order)
        VALUES (?, ?, ?)
    """
    cursor = db_connection.cursor()
    cursor.execute(query, (pool_id, competitor_id, start_order))
    db_connection.commit()


def get_pools_with_competitors(
        db_connection: sqlite3.Connection,
        competition_id: int,
        category_id: int,
        phase: str
) -> List[Dict[str, Any]]:
    query = """
        SELECT p.id, p.name, pc.start_order, c.id, c.first_name, c.last_name, c.nationality
        FROM pool p
        LEFT JOIN pool_competitor pc ON p.id = pc.pool_id
        LEFT JOIN competitor c ON pc.competitor_id = c.id
        WHERE p.competition_id = ? AND p.category_id = ? AND p.phase = ?
        ORDER BY p.name ASC, pc.start_order ASC
    """
    cursor = db_connection.cursor()
    cursor.execute(query, (competition_id, category_id, phase))

    pools_dict: Dict[int, Dict[str, Any]] = {}
    for row in cursor.fetchall():
        p_id, p_name, start_order, c_id, f_name, l_name, nat = row
        if p_id not in pools_dict:
            pools_dict[p_id] = {"id": p_id, "name": p_name, "competitors": []}

        if c_id is not None:
            pools_dict[p_id]["competitors"].append({
                "competitor_id": c_id,
                "first_name": f_name,
                "last_name": l_name,
                "nationality": nat,
                "start_order": start_order
            })

    return list(pools_dict.values())


def get_phase_ranking(
        db_connection: sqlite3.Connection,
        competition_id: int,
        category_id: int,
        phase: str
) -> List[Dict[str, Any]]:
    query = """
        SELECT c.id, c.first_name, c.last_name, c.nationality, MAX(r.final_score) as best_score
        FROM competitor c
        LEFT JOIN run r ON c.id = r.competitor_id AND r.phase = ?
        WHERE c.competition_id = ? AND c.category_id = ?
        GROUP BY c.id
        ORDER BY best_score DESC, c.last_name ASC
    """
    cursor = db_connection.cursor()
    cursor.execute(query, (phase, competition_id, category_id))

    ranking: List[Dict[str, Any]] = []
    for rank, row in enumerate(cursor.fetchall(), start=1):
        c_id, f_name, l_name, nat, best_score = row
        ranking.append({
            "rank": rank,
            "competitor_id": c_id,
            "first_name": f_name,
            "last_name": l_name,
            "nationality": nat,
            "best_score": best_score if best_score is not None else 0.0
        })
    return ranking


def generate_next_phase(
        db_connection: sqlite3.Connection,
        competition_id: int,
        category_id: int,
        current_phase: str,
        next_phase: str,
        top_n: int,
        pools_count: int
) -> List[int]:
    ranking = get_phase_ranking(db_connection, competition_id, category_id, current_phase)
    qualified = ranking[:top_n]

    qualified.reverse()

    base_count = len(qualified) // pools_count
    remainder = len(qualified) % pools_count

    pool_ids: List[int] = []
    current_skater_index = 0

    for i in range(pools_count):
        pool_name = f"Heat {i + 1}"
        pool_data = PoolCreateData(
            competition_id=competition_id,
            category_id=category_id,
            phase=next_phase,
            name=pool_name
        )
        pool_id = create_pool(db_connection, pool_data)
        pool_ids.append(pool_id)

        skaters_in_this_pool = base_count + (1 if i < remainder else 0)

        for start_order in range(1, skaters_in_this_pool + 1):
            if current_skater_index < len(qualified):
                skater = qualified[current_skater_index]
                assign_competitor_to_pool(
                    db_connection,
                    pool_id,
                    skater["competitor_id"],
                    start_order
                )
                current_skater_index += 1

    logger.info(f"Generated {next_phase} with {len(qualified)} skaters in {pools_count} pools.")
    return pool_ids


def export_phase_results_to_excel(
        db_connection: sqlite3.Connection,
        competition_id: int,
        file_path: str
) -> None:
    """Exports all results, grouped by category and phase, into a single Excel file."""
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)

    cursor = db_connection.cursor()

    # Get all categories
    cursor.execute("SELECT id, name FROM category WHERE competition_id = ?", (competition_id,))
    categories = cursor.fetchall()

    phases = ["Qualifications", "Semi-Final", "Final"]

    dns_fill = PatternFill(start_color="FFCDD2", end_color="FFCDD2", fill_type="solid")
    dns_font = Font(color="B71C1C", italic=True)
    header_font = Font(bold=True)

    for cat_id, cat_name in categories:
        for phase in phases:
            ranking = get_phase_ranking(db_connection, competition_id, cat_id, phase)
            if not ranking or all(r["best_score"] == 0.0 for r in ranking):
                continue  # Skip empty phases

            sheet_name = f"{cat_name[:15]}_{phase[:15]}"
            sheet = workbook.create_sheet(title=sheet_name)

            headers = ["Rank", "First Name", "Last Name", "Nationality", "Best Score", "Run 1", "Run 2", "Run 3"]
            sheet.append(headers)

            for cell in sheet[1]:
                cell.font = header_font

            for rank_data in ranking:
                c_id = rank_data["competitor_id"]
                cursor.execute(
                    "SELECT run_number, final_score FROM run WHERE competitor_id = ? AND phase = ?",
                    (c_id, phase)
                )
                runs = {r[0]: r[1] for r in cursor.fetchall()}

                r1 = runs.get(1, "")
                r2 = runs.get(2, "")
                r3 = runs.get(3, "")

                best_score = rank_data["best_score"]
                is_dns = (best_score < 0)

                row_data = [
                    "-" if is_dns else rank_data["rank"],
                    rank_data["first_name"],
                    rank_data["last_name"],
                    rank_data["nationality"],
                    "DNS" if is_dns else round(best_score, 2),
                    "DNS" if r1 == -1.0 else (round(r1, 2) if r1 != "" else ""),
                    "DNS" if r2 == -1.0 else (round(r2, 2) if r2 != "" else ""),
                    "DNS" if r3 == -1.0 else (round(r3, 2) if r3 != "" else "")
                ]

                sheet.append(row_data)

                # Apply DNS styling if best score is < 0
                if is_dns:
                    for cell in sheet[sheet.max_row]:
                        cell.fill = dns_fill
                        cell.font = dns_font

    if not workbook.sheetnames:
        workbook.create_sheet(title="No Results")
        workbook["No Results"].append(["No data available for export."])

    workbook.save(file_path)
    logger.info(f"Results exported successfully to {file_path}")
