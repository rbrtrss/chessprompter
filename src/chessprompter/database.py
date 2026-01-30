"""Database operations for chessprompter using DuckDB."""

import duckdb
from pathlib import Path

from chessprompter.schema import ALL_DDL

DEFAULT_DB_PATH = Path.home() / ".chessprompter" / "games.duckdb"


def get_connection(db_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    """Get a connection to the DuckDB database."""
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def init_db(conn: duckdb.DuckDBPyConnection) -> None:
    """Initialize the database schema."""
    for ddl in ALL_DDL:
        conn.execute(ddl)


def _get_or_create_player(conn: duckdb.DuckDBPyConnection, name: str) -> int:
    """Get or create a player and return their ID."""
    row = conn.execute(
        "SELECT player_id FROM dim_player WHERE name = ?", [name]
    ).fetchone()
    if row:
        return row[0]
    result = conn.execute(
        """
        INSERT INTO dim_player (player_id, name)
        VALUES ((SELECT COALESCE(MAX(player_id), 0) + 1 FROM dim_player), ?)
        RETURNING player_id
        """,
        [name],
    ).fetchone()
    return result[0]


def _get_or_create_date(conn: duckdb.DuckDBPyConnection, year: int | None) -> int:
    """Get or create a date entry and return its ID."""
    row = conn.execute(
        "SELECT date_id FROM dim_date WHERE year IS NOT DISTINCT FROM ?", [year]
    ).fetchone()
    if row:
        return row[0]
    result = conn.execute(
        """
        INSERT INTO dim_date (date_id, year)
        VALUES ((SELECT COALESCE(MAX(date_id), 0) + 1 FROM dim_date), ?)
        RETURNING date_id
        """,
        [year],
    ).fetchone()
    return result[0]


def _get_or_create_event(conn: duckdb.DuckDBPyConnection, name: str | None) -> int:
    """Get or create an event and return its ID."""
    row = conn.execute(
        "SELECT event_id FROM dim_event WHERE name IS NOT DISTINCT FROM ?", [name]
    ).fetchone()
    if row:
        return row[0]
    result = conn.execute(
        """
        INSERT INTO dim_event (event_id, name)
        VALUES ((SELECT COALESCE(MAX(event_id), 0) + 1 FROM dim_event), ?)
        RETURNING event_id
        """,
        [name],
    ).fetchone()
    return result[0]


def _get_or_create_result(conn: duckdb.DuckDBPyConnection, result_str: str | None) -> int:
    """Get or create a result and return its ID."""
    value = result_str or "*"
    row = conn.execute(
        "SELECT result_id FROM dim_result WHERE result = ?", [value]
    ).fetchone()
    if row:
        return row[0]
    result = conn.execute(
        """
        INSERT INTO dim_result (result_id, result)
        VALUES ((SELECT COALESCE(MAX(result_id), 0) + 1 FROM dim_result), ?)
        RETURNING result_id
        """,
        [value],
    ).fetchone()
    return result[0]


def insert_game(
    conn: duckdb.DuckDBPyConnection,
    white: str,
    black: str,
    year: int | None,
    event: str | None,
    result: str | None,
    eco: str | None,
    pgn: str,
    moves: str,
) -> int:
    """Insert a game into the database and return its ID."""
    white_id = _get_or_create_player(conn, white)
    black_id = _get_or_create_player(conn, black)
    date_id = _get_or_create_date(conn, year)
    event_id = _get_or_create_event(conn, event)
    result_id = _get_or_create_result(conn, result)

    result_row = conn.execute(
        """
        INSERT INTO fact_games (game_id, date_id, event_id, white, black, result_id, eco, pgn, moves)
        VALUES ((SELECT COALESCE(MAX(game_id), 0) + 1 FROM fact_games), ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING game_id
        """,
        [date_id, event_id, white_id, black_id, result_id, eco, pgn, moves],
    ).fetchone()
    return result_row[0]


def list_games(conn: duckdb.DuckDBPyConnection) -> list[tuple]:
    """List all games in the database."""
    return conn.execute(
        """
        SELECT
            g.game_id,
            pw.name AS white,
            pb.name AS black,
            d.year,
            -- e.name AS event,
            r.result,
            g.eco
        FROM fact_games g
        JOIN dim_player pw ON g.white = pw.player_id
        JOIN dim_player pb ON g.black = pb.player_id
        JOIN dim_date d ON g.date_id = d.date_id
        -- JOIN dim_event e ON g.event_id = e.event_id
        JOIN dim_result r ON g.result_id = r.result_id
        ORDER BY g.game_id ASC
        """
    ).fetchall()


def get_game(conn: duckdb.DuckDBPyConnection, game_id: int) -> tuple | None:
    """Get a game by its ID."""
    return conn.execute(
        """
        SELECT
            g.game_id,
            pw.name AS white,
            pb.name AS black,
            d.year,
            e.name AS event,
            r.result,
            g.pgn,
            g.moves
        FROM fact_games g
        JOIN dim_player pw ON g.white = pw.player_id
        JOIN dim_player pb ON g.black = pb.player_id
        JOIN dim_date d ON g.date_id = d.date_id
        JOIN dim_event e ON g.event_id = e.event_id
        JOIN dim_result r ON g.result_id = r.result_id
        WHERE g.game_id = ?
        """,
        [game_id],
    ).fetchone()
