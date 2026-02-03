"""Database operations for chessprompter using DuckDB."""

import re
import duckdb
from pathlib import Path

from chessprompter.schema import ALL_DDL

DEFAULT_DB_PATH = Path.home() / ".chessprompter" / "games.duckdb"


def get_connection(db_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    """Get a connection to the DuckDB database."""
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def parse_player_name(name: str) -> dict:
    """Parse a player name into surname, first_name, and display_name.

    Handles formats like:
    - "Anderssen, Adolf" -> surname="Anderssen", first_name="Adolf", display="Adolf Anderssen"
    - "Duke of Brunswick" -> surname="Duke of Brunswick", first_name=None, display="Duke of Brunswick"
    - "Unknown" -> surname="Unknown", first_name=None, display="Unknown"
    """
    name = name.strip()
    if "," in name:
        parts = name.split(",", 1)
        surname = parts[0].strip()
        first_name = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
        if first_name:
            display_name = f"{first_name} {surname}"
        else:
            display_name = surname
    else:
        surname = name
        first_name = None
        display_name = name

    return {
        "surname": surname,
        "first_name": first_name,
        "display_name": display_name,
    }


def detect_consultation_players(name: str) -> list[str]:
    """Detect and split consultation players from a player name string.

    Splits on " and " or " & " patterns.
    Returns a list of individual player names.
    """
    pattern = r'\s+and\s+|\s*&\s*'
    players = re.split(pattern, name, flags=re.IGNORECASE)
    return [p.strip() for p in players if p.strip()]


def _table_exists(conn: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    """Check if a table exists in the database."""
    try:
        conn.execute(f"SELECT 1 FROM {table_name} LIMIT 0")
        return True
    except Exception:
        return False


def _column_exists(conn: duckdb.DuckDBPyConnection, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    try:
        conn.execute(f"SELECT {column_name} FROM {table_name} LIMIT 0")
        return True
    except Exception:
        return False


def migrate_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Migrate old schema to new schema with structured player names."""
    if not _table_exists(conn, "dim_player"):
        return

    # Check if dim_player has the new columns
    if not _column_exists(conn, "dim_player", "display_name"):
        # Add new columns to dim_player
        conn.execute("ALTER TABLE dim_player ADD COLUMN surname TEXT")
        conn.execute("ALTER TABLE dim_player ADD COLUMN first_name TEXT")
        conn.execute("ALTER TABLE dim_player ADD COLUMN display_name TEXT")

        # Populate new columns from existing name field
        players = conn.execute("SELECT player_id, name FROM dim_player").fetchall()
        for player_id, name in players:
            parsed = parse_player_name(name)
            conn.execute(
                "UPDATE dim_player SET surname = ?, first_name = ?, display_name = ? WHERE player_id = ?",
                [parsed["surname"], parsed["first_name"], parsed["display_name"], player_id]
            )

    # Check if fact_games has the new columns
    needs_fact_games_migration = False
    if _table_exists(conn, "fact_games") and not _column_exists(conn, "fact_games", "white_display"):
        conn.execute("ALTER TABLE fact_games ADD COLUMN white_display TEXT")
        conn.execute("ALTER TABLE fact_games ADD COLUMN black_display TEXT")
        conn.execute("ALTER TABLE fact_games ADD COLUMN is_consultation BOOLEAN DEFAULT FALSE")
        needs_fact_games_migration = True

    # Create game_players bridge table if it doesn't exist
    from chessprompter.schema import GAME_PLAYERS_DDL
    conn.execute(GAME_PLAYERS_DDL)

    # Check if any games need migration (have NULL white_display)
    if not _table_exists(conn, "fact_games"):
        return

    games_needing_migration = conn.execute(
        """
        SELECT g.game_id, pw.name AS white_name, pb.name AS black_name, g.white, g.black
        FROM fact_games g
        JOIN dim_player pw ON g.white = pw.player_id
        JOIN dim_player pb ON g.black = pb.player_id
        WHERE g.white_display IS NULL
        """
    ).fetchall()

    for game_id, white_name, black_name, white_id, black_id in games_needing_migration:
        white_players = detect_consultation_players(white_name)
        black_players = detect_consultation_players(black_name)
        is_consultation = len(white_players) > 1 or len(black_players) > 1

        # Build display names
        white_display_parts = []
        for i, player_name in enumerate(white_players, 1):
            parsed = parse_player_name(player_name)
            white_display_parts.append(parsed["display_name"])
            if len(white_players) > 1:
                # Create individual player records if consultation
                player_id = _get_or_create_player(conn, player_name)
                _insert_game_player(conn, game_id, player_id, "white", i)
            else:
                _insert_game_player(conn, game_id, white_id, "white", 1)

        black_display_parts = []
        for i, player_name in enumerate(black_players, 1):
            parsed = parse_player_name(player_name)
            black_display_parts.append(parsed["display_name"])
            if len(black_players) > 1:
                player_id = _get_or_create_player(conn, player_name)
                _insert_game_player(conn, game_id, player_id, "black", i)
            else:
                _insert_game_player(conn, game_id, black_id, "black", 1)

        white_display = " & ".join(white_display_parts)
        black_display = " & ".join(black_display_parts)

        conn.execute(
            "UPDATE fact_games SET white_display = ?, black_display = ?, is_consultation = ? WHERE game_id = ?",
            [white_display, black_display, is_consultation, game_id]
        )


def init_db(conn: duckdb.DuckDBPyConnection) -> None:
    """Initialize the database schema."""
    for ddl in ALL_DDL:
        conn.execute(ddl)
    migrate_schema(conn)


def _get_or_create_player(conn: duckdb.DuckDBPyConnection, name: str) -> int:
    """Get or create a player and return their ID."""
    row = conn.execute(
        "SELECT player_id FROM dim_player WHERE name = ?", [name]
    ).fetchone()
    if row:
        return row[0]

    parsed = parse_player_name(name)
    result = conn.execute(
        """
        INSERT INTO dim_player (player_id, name, surname, first_name, display_name)
        VALUES ((SELECT COALESCE(MAX(player_id), 0) + 1 FROM dim_player), ?, ?, ?, ?)
        RETURNING player_id
        """,
        [name, parsed["surname"], parsed["first_name"], parsed["display_name"]],
    ).fetchone()
    return result[0]


def _insert_game_player(
    conn: duckdb.DuckDBPyConnection,
    game_id: int,
    player_id: int,
    side: str,
    position: int
) -> None:
    """Insert a game-player relationship into the bridge table."""
    # Check if already exists (idempotent)
    existing = conn.execute(
        "SELECT 1 FROM game_players WHERE game_id = ? AND player_id = ? AND side = ?",
        [game_id, player_id, side]
    ).fetchone()
    if existing:
        return

    conn.execute(
        """
        INSERT INTO game_players (game_id, player_id, side, position)
        VALUES (?, ?, ?, ?)
        """,
        [game_id, player_id, side, position]
    )


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
    white_players: list[str],
    black_players: list[str],
    is_consultation: bool,
    year: int | None,
    event: str | None,
    result: str | None,
    eco: str | None,
    moves: str,
) -> int:
    """Insert a game into the database and return its ID."""
    # Create player record for the original name (for backwards compatibility)
    white_id = _get_or_create_player(conn, white)
    black_id = _get_or_create_player(conn, black)
    date_id = _get_or_create_date(conn, year)
    event_id = _get_or_create_event(conn, event)
    result_id = _get_or_create_result(conn, result)

    # Build display names from individual players
    white_display_parts = [parse_player_name(p)["display_name"] for p in white_players]
    black_display_parts = [parse_player_name(p)["display_name"] for p in black_players]
    white_display = " & ".join(white_display_parts)
    black_display = " & ".join(black_display_parts)

    result_row = conn.execute(
        """
        INSERT INTO fact_games (game_id, date_id, event_id, white, black, result_id, eco, moves,
                                white_display, black_display, is_consultation)
        VALUES ((SELECT COALESCE(MAX(game_id), 0) + 1 FROM fact_games), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING game_id
        """,
        [date_id, event_id, white_id, black_id, result_id, eco, moves,
         white_display, black_display, is_consultation],
    ).fetchone()
    game_id = result_row[0]

    # Insert bridge table entries for individual players
    for i, player_name in enumerate(white_players, 1):
        player_id = _get_or_create_player(conn, player_name)
        _insert_game_player(conn, game_id, player_id, "white", i)

    for i, player_name in enumerate(black_players, 1):
        player_id = _get_or_create_player(conn, player_name)
        _insert_game_player(conn, game_id, player_id, "black", i)

    return game_id


def list_games(conn: duckdb.DuckDBPyConnection) -> list[tuple]:
    """List all games in the database."""
    return conn.execute(
        """
        SELECT
            g.game_id,
            g.white_display AS white,
            g.black_display AS black,
            d.year,
            r.result,
            g.eco,
            g.is_consultation
        FROM fact_games g
        JOIN dim_date d ON g.date_id = d.date_id
        JOIN dim_result r ON g.result_id = r.result_id
        ORDER BY g.game_id ASC
        """
    ).fetchall()


def game_exists(conn: duckdb.DuckDBPyConnection, white: str, black: str, moves: str) -> bool:
    """Check if a game with the same players and moves already exists."""
    row = conn.execute(
        """
        SELECT 1 FROM fact_games g
        JOIN dim_player pw ON g.white = pw.player_id
        JOIN dim_player pb ON g.black = pb.player_id
        WHERE pw.name = ? AND pb.name = ? AND g.moves = ?
        LIMIT 1
        """,
        [white, black, moves],
    ).fetchone()
    return row is not None


def get_game(conn: duckdb.DuckDBPyConnection, game_id: int) -> tuple | None:
    """Get a game by its ID."""
    return conn.execute(
        """
        SELECT
            g.game_id,
            g.white_display AS white,
            g.black_display AS black,
            d.year,
            e.name AS event,
            r.result,
            g.moves,
            g.is_consultation
        FROM fact_games g
        JOIN dim_date d ON g.date_id = d.date_id
        JOIN dim_event e ON g.event_id = e.event_id
        JOIN dim_result r ON g.result_id = r.result_id
        WHERE g.game_id = ?
        """,
        [game_id],
    ).fetchone()
