import sqlite3
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_NAME: str = "skate_contest.db"


def get_connection(db_path: str = DB_NAME) -> sqlite3.Connection:
    """
    Creates and returns a connection to the SQLite database.

    Args:
        db_path: The path to the SQLite database file.

    Returns:
        A connection object to the database with foreign keys enabled.
    """
    connection = sqlite3.connect(db_path, check_same_thread=False)
    # Ensure foreign key constraints are strictly enforced in SQLite
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def setup_database(db_path: str = DB_NAME) -> None:
    """
    Initializes the complete database schema with required tables.
    Integrates competition, category, competitor, pool, run, and score tables.
    """
    try:
        with get_connection(db_path) as connection:
            cursor = connection.cursor()

            # 1. Table: competition
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS competition (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    event_date TEXT NOT NULL
                )
            """)

            # 2. Table: category
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS category (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    competition_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    FOREIGN KEY (competition_id) 
                        REFERENCES competition(id) ON DELETE CASCADE,
                    UNIQUE(competition_id, name)
                )
            """)

            # 3. Table: competitor
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS competitor (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    competition_id INTEGER NOT NULL,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    category_id INTEGER NOT NULL,
                    nationality TEXT NOT NULL,
                    FOREIGN KEY (competition_id) 
                        REFERENCES competition(id) ON DELETE CASCADE,
                    FOREIGN KEY (category_id) 
                        REFERENCES category(id) ON DELETE CASCADE,
                    UNIQUE(competition_id, first_name, last_name)
                )
            """)

            # 4. Table: pool
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pool (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    competition_id INTEGER NOT NULL,
                    category_id INTEGER NOT NULL,
                    phase TEXT NOT NULL,
                    name TEXT NOT NULL,
                    FOREIGN KEY (competition_id) 
                        REFERENCES competition(id) ON DELETE CASCADE,
                    FOREIGN KEY (category_id) 
                        REFERENCES category(id) ON DELETE CASCADE,
                    UNIQUE(category_id, phase, name)
                )
            """)

            # 5. Table: pool_competitor
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pool_competitor (
                    pool_id INTEGER NOT NULL,
                    competitor_id INTEGER NOT NULL,
                    start_order INTEGER NOT NULL,
                    PRIMARY KEY (pool_id, competitor_id),
                    FOREIGN KEY (pool_id) 
                        REFERENCES pool(id) ON DELETE CASCADE,
                    FOREIGN KEY (competitor_id) 
                        REFERENCES competitor(id) ON DELETE CASCADE
                )
            """)

            # 6. Table: run
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS run (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    competitor_id INTEGER NOT NULL,
                    phase TEXT NOT NULL,
                    run_number INTEGER NOT NULL,
                    final_score REAL,
                    FOREIGN KEY (competitor_id) 
                        REFERENCES competitor(id) ON DELETE CASCADE,
                    UNIQUE(competitor_id, phase, run_number)
                )
            """)

            # 7. Table: score
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS score (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    judge_id INTEGER NOT NULL,
                    score_value REAL NOT NULL,
                    FOREIGN KEY (run_id) 
                        REFERENCES run(id) ON DELETE CASCADE,
                    UNIQUE(run_id, judge_id)
                )
            """)

            connection.commit()
            logger.info(f"Database schema initialized at {db_path}")

    except sqlite3.Error as error:
        logger.error(f"Failed to initialize the database: {error}")
        raise sqlite3.Error(f"Database setup error: {error}")
