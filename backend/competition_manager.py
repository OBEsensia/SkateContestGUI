import logging
import sqlite3
from dataclasses import dataclass
from typing import Optional, Dict, List, Any
import openpyxl
from openpyxl.styles import Font, PatternFill

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Competition:
    name: str
    event_date: str
    id: Optional[int] = None


@dataclass
class CompetitorRegistration:
    competition_id: int
    first_name: str
    last_name: str
    category: str
    nationality: str


@dataclass
class PoolCreateData:
    competition_id: int
    category_id: int
    phase: str
    name: str


def create_competition(db_connection: sqlite3.Connection, competition_name: str, date_str: str) -> int:
    query = "INSERT INTO competition (name, event_date) VALUES (?, ?)"
    cursor = db_connection.cursor()
    cursor.execute(query, (competition_name, date_str))
    db_connection.commit()
    return cursor.lastrowid


def _get_or_create_category(db_connection: sqlite3.Connection, competition_id: int, category_name: str) -> int:
    cursor = db_connection.cursor()
    cursor.execute("SELECT id FROM category WHERE competition_id = ? AND name = ?", (competition_id, category_name))
    row = cursor.fetchone()
    if row: return row[0]
    cursor.execute("INSERT INTO category (competition_id, name) VALUES (?, ?)", (competition_id, category_name))
    db_connection.commit()
    return cursor.lastrowid


def register_competitor_manually(db_connection: sqlite3.Connection, registration: CompetitorRegistration) -> int:
    category_id = _get_or_create_category(db_connection, registration.competition_id, registration.category)
    query = """
        INSERT INTO competitor (competition_id, first_name, last_name, category_id, nationality) 
        VALUES (?, ?, ?, ?, ?)
    """
    try:
        cursor = db_connection.cursor()
        cursor.execute(query, (
            registration.competition_id, registration.first_name, registration.last_name, category_id,
            registration.nationality))
        db_connection.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError(
            f"Could not register competitor. {registration.first_name} {registration.last_name} might already exist.")


def _find_column_index(headers: Dict[int, str], possible_names: List[str]) -> Optional[int]:
    for col_idx, header_val in headers.items():
        if header_val.strip().lower() in possible_names: return col_idx
    for col_idx, header_val in headers.items():
        clean_header = header_val.strip().lower()
        for name in possible_names:
            if name == "nom" and ("pre" in clean_header or "pré" in clean_header): continue
            if name in clean_header: return col_idx
    return None


def import_competitors_from_excel(db_connection: sqlite3.Connection, file_path: str, competition_id: int) -> int:
    try:
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook.active
    except Exception:
        raise ValueError("Invalid Excel document.")

    headers: Dict[int, str] = {}
    for col_idx, cell in enumerate(sheet[1], start=1):
        if cell.value: headers[col_idx] = str(cell.value)

    first_name_idx = _find_column_index(headers, ["first", "prenom", "prénom", "name"])
    last_name_idx = _find_column_index(headers, ["last", "nom", "family"])
    category_idx = _find_column_index(headers, ["cat", "division"])
    nationality_idx = _find_column_index(headers, ["nat", "country", "pays"])

    if not first_name_idx or not last_name_idx:
        raise KeyError("Could not find required 'First Name' and 'Last Name' columns.")

    imported_count = 0
    for row_index in range(2, sheet.max_row + 1):
        first_name = sheet.cell(row=row_index, column=first_name_idx).value
        last_name = sheet.cell(row=row_index, column=last_name_idx).value
        if not first_name or not last_name: continue

        category_val = str(sheet.cell(row=row_index, column=category_idx).value).strip() if category_idx and sheet.cell(
            row=row_index, column=category_idx).value else "Open Boy"
        nationality_val = str(
            sheet.cell(row=row_index, column=nationality_idx).value).strip() if nationality_idx and sheet.cell(
            row=row_index, column=nationality_idx).value else "FRA"

        reg = CompetitorRegistration(competition_id, str(first_name).strip(), str(last_name).strip(), category_val,
                                     nationality_val.upper())
        try:
            register_competitor_manually(db_connection, reg)
            imported_count += 1
        except ValueError:
            pass
    return imported_count


def create_pool(db_connection: sqlite3.Connection, pool_data: PoolCreateData) -> int:
    query = "INSERT INTO pool (competition_id, category_id, phase, name) VALUES (?, ?, ?, ?)"
    try:
        cursor = db_connection.cursor()
        cursor.execute(query, (pool_data.competition_id, pool_data.category_id, pool_data.phase, pool_data.name))
        db_connection.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError(f"Pool '{pool_data.name}' already exists.")


def assign_competitor_to_pool(db_connection: sqlite3.Connection, pool_id: int, competitor_id: int,
                              start_order: int) -> None:
    query = "INSERT OR REPLACE INTO pool_competitor (pool_id, competitor_id, start_order) VALUES (?, ?, ?)"
    cursor = db_connection.cursor()
    cursor.execute(query, (pool_id, competitor_id, start_order))
    db_connection.commit()


def get_pools_with_competitors(db_connection: sqlite3.Connection, competition_id: int, category_id: int, phase: str,
                               run_number: Optional[int] = None) -> List[Dict[str, Any]]:
    if run_number is not None:
        query = """
            SELECT p.id, p.name, pc.start_order, c.id, c.first_name, c.last_name, c.nationality, r.final_score
            FROM pool p
            LEFT JOIN pool_competitor pc ON p.id = pc.pool_id
            LEFT JOIN competitor c ON pc.competitor_id = c.id
            LEFT JOIN run r ON c.id = r.competitor_id AND r.phase = p.phase AND r.run_number = ?
            WHERE p.competition_id = ? AND p.category_id = ? AND p.phase = ?
            ORDER BY p.name ASC, pc.start_order ASC
        """
        params = (run_number, competition_id, category_id, phase)
    else:
        query = """
            SELECT p.id, p.name, pc.start_order, c.id, c.first_name, c.last_name, c.nationality, NULL
            FROM pool p
            LEFT JOIN pool_competitor pc ON p.id = pc.pool_id
            LEFT JOIN competitor c ON pc.competitor_id = c.id
            WHERE p.competition_id = ? AND p.category_id = ? AND p.phase = ?
            ORDER BY p.name ASC, pc.start_order ASC
        """
        params = (competition_id, category_id, phase)

    cursor = db_connection.cursor()
    cursor.execute(query, params)

    pools_dict: Dict[int, Dict[str, Any]] = {}
    for row in cursor.fetchall():
        p_id, p_name, start_order, c_id, f_name, l_name, nat, score = row
        if p_id not in pools_dict: pools_dict[p_id] = {"id": p_id, "name": p_name, "competitors": []}
        if c_id is not None:
            pools_dict[p_id]["competitors"].append({
                "competitor_id": c_id, "first_name": f_name, "last_name": l_name,
                "nationality": nat, "start_order": start_order,
                "current_run_score": score
            })
    return list(pools_dict.values())


def get_phase_ranking(db_connection: sqlite3.Connection, competition_id: int, category_id: int, phase: str) -> List[
    Dict[str, Any]]:
    cursor = db_connection.cursor()
    query = """
        SELECT c.id, c.first_name, c.last_name, c.nationality,
               COALESCE(MAX(r.final_score), 0.0) as best_score,
               p.name as pool_name,
               pc.start_order
        FROM competitor c
        JOIN pool_competitor pc ON c.id = pc.competitor_id
        JOIN pool p ON pc.pool_id = p.id AND p.phase = ?
        LEFT JOIN run r ON c.id = r.competitor_id AND r.phase = ?
        WHERE c.competition_id = ? AND c.category_id = ?
        GROUP BY c.id
        ORDER BY best_score DESC, pool_name ASC, pc.start_order ASC
    """
    cursor.execute(query, (phase, phase, competition_id, category_id))
    competitors_data = cursor.fetchall()

    cursor.execute("SELECT competitor_id, run_number, final_score FROM run WHERE phase = ?", (phase,))
    all_runs = cursor.fetchall()

    runs_by_competitor = {}
    for c_id, r_num, f_score in all_runs:
        if c_id not in runs_by_competitor:
            runs_by_competitor[c_id] = {}
        runs_by_competitor[c_id][r_num] = f_score

    ranking: List[Dict[str, Any]] = []
    rank_counter = 1
    for row in competitors_data:
        c_id, f_name, l_name, nat, best_score, pool_name, start_order = row
        is_dns = (best_score < 0)
        c_runs = runs_by_competitor.get(c_id, {})

        ranking.append({
            "rank": "-" if is_dns else rank_counter,
            "competitor_id": c_id,
            "first_name": f_name,
            "last_name": l_name,
            "nationality": nat,
            "best_score": best_score,
            "run_scores": c_runs
        })
        if not is_dns:
            rank_counter += 1
    return ranking


def generate_next_phase(db_connection: sqlite3.Connection, competition_id: int, category_id: int, current_phase: str,
                        next_phase: str, top_n: int, pools_count: int) -> List[int]:
    ranking = get_phase_ranking(db_connection, competition_id, category_id, current_phase)
    qualified = [r for r in ranking if r["best_score"] >= 0][:top_n]
    qualified.reverse()

    base_count = len(qualified) // pools_count
    remainder = len(qualified) % pools_count

    pool_ids: List[int] = []
    current_skater_idx = 0

    for i in range(pools_count):
        pool_id = create_pool(db_connection, PoolCreateData(competition_id, category_id, next_phase, f"Heat {i + 1}"))
        pool_ids.append(pool_id)

        skaters_in_this_pool = base_count + (1 if i < remainder else 0)
        for start_order in range(1, skaters_in_this_pool + 1):
            if current_skater_idx < len(qualified):
                assign_competitor_to_pool(db_connection, pool_id, qualified[current_skater_idx]["competitor_id"],
                                          start_order)
                current_skater_idx += 1

    return pool_ids


def export_phase_results_to_excel(db_connection: sqlite3.Connection, competition_id: int, file_path: str) -> None:
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)

    cursor = db_connection.cursor()
    cursor.execute("SELECT id, name FROM category WHERE competition_id = ?", (competition_id,))
    categories = cursor.fetchall()

    phases = ["Qualifications", "Semi-Final", "Final"]
    next_phase_map = {"Qualifications": "Semi-Final", "Semi-Final": "Final", "Final": None}

    dns_fill = PatternFill(start_color="FFCDD2", end_color="FFCDD2", fill_type="solid")
    dns_font = Font(color="B71C1C", italic=True)
    header_font = Font(bold=True)

    for cat_id, cat_name in categories:
        for phase in phases:
            cursor.execute("""
                SELECT 1 FROM pool_competitor pc 
                JOIN pool p ON pc.pool_id = p.id 
                WHERE p.competition_id = ? AND p.category_id = ? AND p.phase = ? LIMIT 1
            """, (competition_id, cat_id, phase))
            if not cursor.fetchone(): continue

            ranking = get_phase_ranking(db_connection, competition_id, cat_id, phase)
            sheet_name = f"{cat_name[:15]}_{phase[:15]}"
            sheet = workbook.create_sheet(title=sheet_name)

            # Detect max runs dynamically
            max_run_num = 0
            for r in ranking:
                if r["run_scores"]:
                    max_run_num = max(max_run_num, max(r["run_scores"].keys()))
            max_runs_to_display = max(2, max_run_num)

            next_phase = next_phase_map.get(phase)
            headers = ["Rank", "First Name", "Last Name", "Nationality", "Best Score"]
            for i in range(1, max_runs_to_display + 1):
                headers.append(f"Run {i}")

            if next_phase:
                headers.extend([f"Qualified for {next_phase}?", f"Heat ({next_phase})", f"Order ({next_phase})"])

            sheet.append(headers)
            for cell in sheet[1]: cell.font = header_font

            for rank_data in ranking:
                c_id = rank_data["competitor_id"]
                best_score = rank_data["best_score"]
                is_dns = (best_score < 0)

                row_data = [
                    rank_data["rank"],
                    rank_data["first_name"],
                    rank_data["last_name"],
                    rank_data["nationality"],
                    "DNS" if is_dns else round(best_score, 2)
                ]

                for i in range(1, max_runs_to_display + 1):
                    r_score = rank_data["run_scores"].get(i, "")
                    if r_score == -1.0:
                        row_data.append("DNS")
                    elif r_score != "":
                        row_data.append(round(r_score, 2))
                    else:
                        row_data.append("")

                if next_phase:
                    cursor.execute("""
                        SELECT p.name, pc.start_order FROM pool_competitor pc
                        JOIN pool p ON pc.pool_id = p.id
                        WHERE pc.competitor_id = ? AND p.phase = ?
                    """, (c_id, next_phase))
                    next_assignment = cursor.fetchone()
                    if next_assignment:
                        row_data.extend(["YES", next_assignment[0], next_assignment[1]])
                    else:
                        row_data.extend(["NO", "-", "-"])

                sheet.append(row_data)

                if is_dns:
                    for cell in sheet[sheet.max_row]:
                        cell.fill = dns_fill
                        cell.font = dns_font

    if not workbook.sheetnames:
        workbook.create_sheet(title="No Results")
        workbook["No Results"].append(["No data available for export."])

    workbook.save(file_path)
    logger.info(f"Results exported successfully to {file_path}")
