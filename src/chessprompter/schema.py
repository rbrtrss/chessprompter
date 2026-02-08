"""DDL definitions for the star schema of chess games"""

DIM_PLAYER_DDL = """
CREATE TABLE IF NOT EXISTS dim_player (
    player_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    surname TEXT,
    first_name TEXT,
    display_name TEXT NOT NULL
);
"""

DIM_DATE_DDL = """
CREATE TABLE IF NOT EXISTS dim_date (
    date_id INTEGER PRIMARY KEY,
    date TEXT,
    year INTEGER,
    month INTEGER,
    day INTEGER
);
"""

DIM_EVENT_DDL = """
CREATE TABLE IF NOT EXISTS dim_event (
    event_id INTEGER PRIMARY KEY,
    name TEXT,
    site TEXT,
    round TEXT
);
"""

DIM_RESULT_DDL = """
CREATE TABLE IF NOT EXISTS dim_result (
    result_id INTEGER PRIMARY KEY,
    result TEXT NOT NULL UNIQUE
);
"""

FACT_GAMES_DDL = """
CREATE TABLE IF NOT EXISTS fact_games (
    game_id INTEGER NOT NULL,
    date_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    playing_white_id INTEGER NOT NULL,
    playing_black_id INTEGER NOT NULL,
    result_id INTEGER NOT NULL,
    eco TEXT,
    moves TEXT,
    white_display TEXT,
    black_display TEXT,
    is_consultation BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (game_id),
    FOREIGN KEY (playing_white_id) REFERENCES dim_player(player_id),
    FOREIGN KEY (playing_black_id) REFERENCES dim_player(player_id),
    FOREIGN KEY (date_id) REFERENCES dim_date(date_id),
    FOREIGN KEY (event_id) REFERENCES dim_event(event_id),
    FOREIGN KEY (result_id) REFERENCES dim_result(result_id)
);
"""

GAME_PLAYERS_DDL = """
CREATE TABLE IF NOT EXISTS game_players (
    game_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('white', 'black')),
    position INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (game_id, player_id, side),
    FOREIGN KEY (game_id) REFERENCES fact_games(game_id),
    FOREIGN KEY (player_id) REFERENCES dim_player(player_id)
);
"""

# Order for table creation (dimensions before fact)
ALL_DDL = [DIM_PLAYER_DDL, DIM_DATE_DDL, DIM_EVENT_DDL, DIM_RESULT_DDL, FACT_GAMES_DDL, GAME_PLAYERS_DDL]