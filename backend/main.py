import logging
import json
import os
import shutil
import sqlite3
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any, Iterator

from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    Depends,
    UploadFile,
    File
)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from db_manager import setup_database, get_connection
from competition_manager import (
    create_competition,
    register_competitor_manually,
    import_competitors_from_excel,
    create_pool,
    assign_competitor_to_pool,
    get_pools_with_competitors,
    get_phase_ranking,
    generate_next_phase,
    export_phase_results_to_excel,
    CompetitorRegistration,
    PoolCreateData
)

import mimetypes

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    logger.info("Starting up server, initializing database schema...")
    setup_database()
    yield
    logger.info("Shutting down server...")


app = FastAPI(lifespan=lifespan)


def get_db_connection() -> Iterator[sqlite3.Connection]:
    connection = get_connection()
    try:
        yield connection
    finally:
        connection.close()


class CompetitionCreate(BaseModel):
    name: str
    event_date: str


class CompetitorCreate(BaseModel):
    first_name: str
    last_name: str
    category: str
    nationality: str


class PoolCreate(BaseModel):
    competition_id: int
    category_id: int
    phase: str
    name: str


class PoolAssign(BaseModel):
    pool_id: int
    competitor_id: int
    start_order: int


class GeneratePhaseRequest(BaseModel):
    current_phase: str
    next_phase: str
    top_n: int
    pools_count: int


@app.post("/competitions/")
def create_new_competition(
        competition_data: CompetitionCreate,
        db_conn: sqlite3.Connection = Depends(get_db_connection)
) -> Dict[str, int]:
    try:
        competition_id = create_competition(
            db_conn,
            competition_name=competition_data.name,
            date_str=competition_data.event_date
        )
        return {"competition_id": competition_id}
    except Exception as error:
        logger.error(f"Error creating competition: {error}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/competitions/")
def get_all_competitions(
        db_conn: sqlite3.Connection = Depends(get_db_connection)
) -> List[Dict[str, Any]]:
    try:
        cursor = db_conn.cursor()
        cursor.execute("SELECT id, name, event_date FROM competition ORDER BY id DESC")
        rows = cursor.fetchall()
        return [{"id": row[0], "name": row[1], "event_date": row[2]} for row in rows]
    except Exception as error:
        logger.error(f"Error fetching competitions: {error}")
        raise HTTPException(status_code=500, detail="Database error")


@app.get("/competitions/{competition_id}/categories/")
def get_categories(
        competition_id: int,
        db_conn: sqlite3.Connection = Depends(get_db_connection)
) -> List[Dict[str, Any]]:
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT id, name FROM category WHERE competition_id = ? ORDER BY name ASC",
            (competition_id,)
        )
        rows = cursor.fetchall()
        return [{"id": r[0], "name": r[1]} for r in rows]
    except Exception as error:
        logger.error(f"Error fetching categories: {error}")
        raise HTTPException(status_code=500, detail="Database error")


@app.post("/competitions/{competition_id}/competitors/")
def register_competitor(
        competition_id: int,
        competitor_data: CompetitorCreate,
        db_conn: sqlite3.Connection = Depends(get_db_connection)
) -> Dict[str, int]:
    registration = CompetitorRegistration(
        competition_id=competition_id,
        first_name=competitor_data.first_name,
        last_name=competitor_data.last_name,
        category=competitor_data.category,
        nationality=competitor_data.nationality
    )
    try:
        competitor_id = register_competitor_manually(db_conn, registration)
        return {"competitor_id": competitor_id}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.post("/competitions/{competition_id}/import-excel/")
def upload_competitors_excel(
        competition_id: int,
        file: UploadFile = File(...),
        db_conn: sqlite3.Connection = Depends(get_db_connection)
) -> Dict[str, int]:
    if not file.filename or not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Invalid file format.")

    temp_file_path = f"temp_{file.filename}"
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        imported_count = import_competitors_from_excel(
            db_conn,
            file_path=temp_file_path,
            competition_id=competition_id
        )
        return {"imported_count": imported_count}
    except KeyError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@app.get("/competitions/{competition_id}/competitors/")
def get_competitors_for_competition(
        competition_id: int,
        db_conn: sqlite3.Connection = Depends(get_db_connection)
) -> List[Dict[str, Any]]:
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            """
            SELECT c.id, c.first_name, c.last_name, cat.name as category, cat.id as category_id, c.nationality 
            FROM competitor c
            JOIN category cat ON c.category_id = cat.id
            WHERE c.competition_id = ? 
            ORDER BY cat.name ASC, c.last_name ASC
            """,
            (competition_id,)
        )
        rows = cursor.fetchall()
        return [
            {
                "id": r[0],
                "first_name": r[1],
                "last_name": r[2],
                "category": r[3],
                "category_id": r[4],
                "nationality": r[5]
            } for r in rows
        ]
    except Exception as error:
        logger.error(f"Error fetching competitors: {error}")
        raise HTTPException(status_code=500, detail="Database error")


@app.post("/pools/")
def create_new_pool(
        pool_data: PoolCreate,
        db_conn: sqlite3.Connection = Depends(get_db_connection)
) -> Dict[str, int]:
    try:
        data = PoolCreateData(
            competition_id=pool_data.competition_id,
            category_id=pool_data.category_id,
            phase=pool_data.phase,
            name=pool_data.name
        )
        pool_id = create_pool(db_conn, data)
        return {"pool_id": pool_id}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.post("/pools/assign/")
def assign_skater_to_pool(
        assign_data: PoolAssign,
        db_conn: sqlite3.Connection = Depends(get_db_connection)
) -> Dict[str, str]:
    try:
        assign_competitor_to_pool(
            db_conn,
            pool_id=assign_data.pool_id,
            competitor_id=assign_data.competitor_id,
            start_order=assign_data.start_order
        )
        return {"status": "success"}
    except Exception as error:
        logger.error(f"Error assigning skater to pool: {error}")
        raise HTTPException(status_code=500, detail="Database error")


@app.get("/competitions/{competition_id}/categories/{category_id}/pools/")
def get_pools_for_category(
        competition_id: int,
        category_id: int,
        phase: str,
        db_conn: sqlite3.Connection = Depends(get_db_connection)
) -> List[Dict[str, Any]]:
    try:
        return get_pools_with_competitors(db_conn, competition_id, category_id, phase)
    except Exception as error:
        logger.error(f"Error fetching pools: {error}")
        raise HTTPException(status_code=500, detail="Database error")


@app.get("/competitions/{competition_id}/categories/{category_id}/rankings/")
def get_rankings(
        competition_id: int,
        category_id: int,
        phase: str,
        db_conn: sqlite3.Connection = Depends(get_db_connection)
) -> List[Dict[str, Any]]:
    try:
        return get_phase_ranking(db_conn, competition_id, category_id, phase)
    except Exception as error:
        logger.error(f"Error fetching rankings: {error}")
        raise HTTPException(status_code=500, detail="Database error")


@app.post("/competitions/{competition_id}/categories/{category_id}/generate-phase/")
def generate_phase(
        competition_id: int,
        category_id: int,
        request_data: GeneratePhaseRequest,
        db_conn: sqlite3.Connection = Depends(get_db_connection)
) -> Dict[str, Any]:
    try:
        pool_ids = generate_next_phase(
            db_connection=db_conn,
            competition_id=competition_id,
            category_id=category_id,
            current_phase=request_data.current_phase,
            next_phase=request_data.next_phase,
            top_n=request_data.top_n,
            pools_count=request_data.pools_count
        )
        return {"status": "success", "generated_pools": len(pool_ids)}
    except Exception as error:
        logger.error(f"Error generating phase: {error}")
        raise HTTPException(status_code=500, detail="Database error")


@app.get("/competitions/{competition_id}/export-results/")
def export_results(
        competition_id: int,
        db_conn: sqlite3.Connection = Depends(get_db_connection)
) -> FileResponse:
    try:
        file_path = f"export_competition_{competition_id}.xlsx"
        export_phase_results_to_excel(db_conn, competition_id, file_path)

        return FileResponse(
            path=file_path,
            filename=f"Skate_Contest_Results_{competition_id}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as error:
        logger.error(f"Error exporting results: {error}")
        raise HTTPException(status_code=500, detail="Internal server error")


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []
        self.cached_meta: Dict[str, Any] = {}
        self.cached_run: Dict[str, Any] = {}
        self.cached_voting: Dict[str, Any] = {}
        self.cached_podium: Dict[str, Any] = {}
        self.cached_leaderboard: Dict[str, Any] = {}

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

        if self.cached_meta:
            await websocket.send_json(self.cached_meta)
        if self.cached_leaderboard:
            await websocket.send_json(self.cached_leaderboard)
        if self.cached_podium:
            await websocket.send_json(self.cached_podium)
        elif self.cached_run:
            await websocket.send_json(self.cached_run)
            if self.cached_voting:
                await websocket.send_json(self.cached_voting)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.remove(websocket)

    async def broadcast_json(self, message: Dict[str, Any]) -> None:
        msg_type = message.get("type")

        if msg_type == "board_meta":
            self.cached_meta = message
        elif msg_type == "new_run":
            self.cached_run = message
            self.cached_voting = {}
            self.cached_podium = {}
        elif msg_type == "voting_opened":
            self.cached_voting = message
        elif msg_type == "podium_mode":
            self.cached_podium = message
        elif msg_type == "leaderboard_updated":
            self.cached_leaderboard = message

        for connection in self.active_connections:
            await connection.send_json(message)


global_manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await global_manager.connect(websocket)

    await websocket.send_json({
        "type": "board_meta",
        "competition_name": getattr(global_manager, "competition_name", "SKATE CONTEST"),
        "judge_count": getattr(global_manager, "judge_count", 5)
    })

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "start_live":
                global_manager.judge_count = data.get("judge_count", 3)
                global_manager.competition_name = data.get("competition_name", "SKATE CONTEST")
                await global_manager.broadcast_json({
                    "type": "board_meta",
                    "competition_name": global_manager.competition_name,
                    "judge_count": global_manager.judge_count
                })

            elif action == "call_skater":
                global_manager.received_scores = {}
                await global_manager.broadcast_json({
                    "type": "new_run",
                    "competitor_id": data.get("competitor_id"),
                    "skater_name": data.get("skater_name", ""),
                    "category": data.get("category", ""),
                    "nationality": data.get("nationality", ""),
                    "phase": data.get("phase", "Qualifications"),
                    "run_number": data.get("run_number")
                })

            elif action == "open_voting":
                await global_manager.broadcast_json({
                    "type": "voting_opened"
                })

            elif action == "dns_skater":
                global_manager.received_scores = {}

                # Update database directly from WebSocket for critical DNS
                db_conn = get_connection()
                cursor = db_conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO run (competitor_id, phase, run_number, final_score) VALUES (?, ?, ?, ?)",
                    (global_manager.cached_run.get("competitor_id"), global_manager.cached_run.get("phase"),
                     global_manager.cached_run.get("run_number"), -1.0)
                )
                db_conn.commit()
                db_conn.close()

                await global_manager.broadcast_json({
                    "type": "run_completed",
                    "final_score": -1.0,
                    "is_dns": True
                })

            elif action == "show_podium":
                await global_manager.broadcast_json({
                    "type": "podium_mode",
                    "leaderboard": data.get("leaderboard", [])
                })

            elif action == "submit_score":
                judge_id = data.get("judge_id")
                score = data.get("score")
                global_manager.received_scores[judge_id] = score

                await global_manager.broadcast_json({
                    "type": "score_received",
                    "judge_id": judge_id
                })

                current_judge_count = getattr(global_manager, "judge_count", 3)
                if len(global_manager.received_scores) >= current_judge_count:
                    # Implement drop high/low for 5 judges logic here if requested, currently doing simple average
                    final_score = sum(global_manager.received_scores.values()) / current_judge_count

                    # Update database directly from WebSocket
                    db_conn = get_connection()
                    cursor = db_conn.cursor()
                    cursor.execute(
                        "INSERT OR REPLACE INTO run (competitor_id, phase, run_number, final_score) VALUES (?, ?, ?, ?)",
                        (global_manager.cached_run.get("competitor_id"), global_manager.cached_run.get("phase"),
                         global_manager.cached_run.get("run_number"), final_score)
                    )
                    db_conn.commit()
                    db_conn.close()

                    await global_manager.broadcast_json({
                        "type": "run_completed",
                        "final_score": final_score,
                        "is_dns": False
                    })

            elif action == "update_leaderboard":
                await global_manager.broadcast_json({
                    "type": "leaderboard_updated",
                    "leaderboard": data.get("leaderboard", [])
                })

    except WebSocketDisconnect:
        global_manager.disconnect(websocket)
    except Exception as error:
        logger.error(f"Error in WebSocket loop: {error}")


STATIC_DIR = "static"
if os.path.exists(STATIC_DIR) and os.path.isdir(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
