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
from pydantic import BaseModel
from dataclasses import dataclass, field

from db_manager import setup_database, get_connection
from competition_manager import (
    create_competition,
    register_competitor_manually,
    import_competitors_from_excel,
    CompetitorRegistration
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
    bib_number: int


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
        bib_number=competitor_data.bib_number
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
            """SELECT id, first_name, last_name, bib_number FROM competitor 
               WHERE competition_id = ? ORDER BY bib_number ASC""",
            (competition_id,)
        )
        rows = cursor.fetchall()
        return [{"id": r[0], "first_name": r[1], "last_name": r[2], "bib_number": r[3]} for r in rows]
    except Exception as error:
        logger.error(f"Error fetching competitors: {error}")
        raise HTTPException(status_code=500, detail="Database error")


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []
        # Le cache complet des derniers événements
        self.cached_meta: Dict[str, Any] = {}
        self.cached_run: Dict[str, Any] = {}
        self.cached_voting: Dict[str, Any] = {}
        self.cached_podium: Dict[str, Any] = {}
        self.cached_leaderboard: Dict[str, Any] = {}

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

        # Rattrapage (Catch-up) immédiat pour celui qui se connecte
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

        # Mise à jour intelligente du cache
        if msg_type == "board_meta":
            self.cached_meta = message
        elif msg_type == "new_run":
            self.cached_run = message
            self.cached_voting = {}  # Réinitialise l'état de vote
            self.cached_podium = {}  # Quitte le mode podium
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

    # Informer explicitement de la configuration
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
                    "run_number": data.get("run_number")
                })

            elif action == "open_voting":
                await global_manager.broadcast_json({
                    "type": "voting_opened"
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
                    final_score = sum(global_manager.received_scores.values()) / current_judge_count
                    await global_manager.broadcast_json({
                        "type": "run_completed",
                        "final_score": final_score
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
