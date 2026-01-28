"""Database operations for chessprompter using DuckDB."""

import duckdb
from pathlib import Path

DEFAULT_DB_PATH = Path.home() / ".chessprompter" / "games.duckdb"


def get_connection(db_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    """Get a connection to the DuckDB database."""
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def init_db(conn: duckdb.DuckDBPyConnection) -> None:
    """Initialize the database schema."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY,
            white VARCHAR,
            black VARCHAR,
            year INTEGER,
            event VARCHAR,
            result VARCHAR,
            pgn TEXT,
            moves TEXT
        )
    """)
    conn.execute("""
        CREATE SEQUENCE IF NOT EXISTS games_id_seq START 1
    """)


def insert_game(
    conn: duckdb.DuckDBPyConnection,
    white: str,
    black: str,
    year: int | None,
    event: str | None,
    result: str | None,
    pgn: str,
    moves: str,
) -> int:
    """Insert a game into the database and return its ID."""
    result_row = conn.execute(
        """
        INSERT INTO games (id, white, black, year, event, result, pgn, moves)
        VALUES (nextval('games_id_seq'), ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
        """,
        [white, black, year, event, result, pgn, moves],
    ).fetchone()
    return result_row[0]


def list_games(conn: duckdb.DuckDBPyConnection) -> list[tuple]:
    """List all games in the database."""
    return conn.execute(
        """
        SELECT id, white, black, year, event, result
        FROM games
        ORDER BY year DESC NULLS LAST, id DESC
        """
    ).fetchall()


def get_game(conn: duckdb.DuckDBPyConnection, game_id: int) -> tuple | None:
    """Get a game by its ID."""
    result = conn.execute(
        """
        SELECT id, white, black, year, event, result, pgn, moves
        FROM games
        WHERE id = ?
        """,
        [game_id],
    ).fetchone()
    return result
