# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

chessprompter is a minimalistic CLI tool for training chess with a physical board. It displays chess game moves sequentially from PGN files, allowing users to follow along on their physical board without distractions.

## Development Commands

```bash
# Install in development mode
pip install -e .

# Run the CLI
chessprompter load game.pgn     # Import PGN files into database
chessprompter list              # List all loaded games
chessprompter play <game_id>    # Step through a game move by move
```

## Architecture

The codebase follows a simple layered structure in `src/chessprompter/`:

- **cli.py**: Click-based CLI entry point. Defines commands (load, list, play) and orchestrates the other modules.
- **pgn_parser.py**: Parses PGN files using the `chess` library. Yields `ParsedGame` dataclass instances with extracted metadata and SAN move lists.
- **schema.py**: DDL definitions for the star schema database structure.
- **database.py**: DuckDB persistence layer using a star schema. Games are stored in `~/.chessprompter/games.duckdb`.
- **player.py**: Terminal-based interactive player. Uses raw terminal input (`tty`/`termios`) for single-keypress navigation through moves.

### Database Schema

The database uses a star schema with the following tables:

- **dim_player**: Player dimension with parsed name fields (surname, first_name, display_name)
- **dim_date**: Date dimension (year, month, day)
- **dim_event**: Event dimension (name, site, round)
- **dim_result**: Result dimension (1-0, 0-1, 1/2-1/2, *)
- **fact_games**: Central fact table linking to dimensions, stores moves and PGN
- **game_players**: Bridge table for consultation games (supports multiple players per side)

## Key Dependencies

- `chess`: PGN parsing and move validation
- `duckdb`: Local database storage
- `click`: CLI framework
