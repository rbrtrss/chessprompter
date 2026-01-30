"""DDL definitions for the star schema of chess games"""

DIM_PLAYER_DDL = """
CREATE TABLE IF NOT EXISTS dim_player (
    player_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
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
    white INTEGER NOT NULL,
    black INTEGER NOT NULL,
    result_id INTEGER NOT NULL,
    eco TEXT,
    pgn TEXT,
    moves TEXT,
    PRIMARY KEY (game_id),
    FOREIGN KEY (white) REFERENCES dim_player(player_id),
    FOREIGN KEY (black) REFERENCES dim_player(player_id),
    FOREIGN KEY (date_id) REFERENCES dim_date(date_id),
    FOREIGN KEY (event_id) REFERENCES dim_event(event_id),
    FOREIGN KEY (result_id) REFERENCES dim_result(result_id)
);
"""

# Order for table creation (dimensions before fact)
ALL_DDL = [DIM_PLAYER_DDL, DIM_DATE_DDL, DIM_EVENT_DDL, DIM_RESULT_DDL, FACT_GAMES_DDL]