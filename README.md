# chessprompter

chessprompter is a command line tool that shows the plays of a chess game sequentially. It is intended as a minimalistic aid tool for training with a physical board without distractions. Games are loaded in PGN format.

## Installation

```bash
git clone https://github.com/yourusername/chessprompter.git
cd chessprompter
uv tool install .
```

## Usage

### Load PGN files

Import games from PGN files into the local database:

```bash
chessprompter load game1.pgn game2.pgn
```

### List games

View all loaded games:

```bash
chessprompter list
```

This displays a table with game ID, players, year, result, and event.

### Play through a game

Step through a game move by move:

```bash
chessprompter play <game_id>
```

Controls:
- `n` - next move
- `b` - previous move
- `q` - quit

### Options

Specify a custom database location:

```bash
chessprompter --db /path/to/games.duckdb load game.pgn
```

By default, games are stored in `~/.chessprompter/games.duckdb`.

## Analytics with dbt

The project includes a [dbt](https://docs.getdbt.com/) project (`chessprompter_dbt/`) that transforms the raw star schema into analytical models. It uses the `dbt-duckdb` adapter to work directly with the same DuckDB database.

See the [tutorial](chessprompter_dbt/TUTORIAL.md) for a detailed walkthrough of the dbt setup and concepts.

### Running dbt

All dbt commands must be run from the `chessprompter_dbt/` directory:

```bash
cd chessprompter_dbt
```

Build all models and run tests:

```bash
uv run dbt build
```

Run models only (without tests):

```bash
uv run dbt run
```

Run tests only:

```bash
uv run dbt test
```

### Models

- **Staging**: `stg_games` — denormalized view joining fact and dimension tables
- **Marts**: `player_stats` — win/loss/draw statistics per player
- **Marts**: `opening_stats` — performance statistics by ECO opening code

## Database Schema

See [schema-diagram.md](schema-diagram.md) for the ER diagram.
