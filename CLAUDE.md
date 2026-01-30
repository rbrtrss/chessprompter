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
- **database.py**: DuckDB persistence layer. Games are stored in `~/.chessprompter/games.duckdb` with a single `games` table.
- **player.py**: Terminal-based interactive player. Uses raw terminal input (`tty`/`termios`) for single-keypress navigation through moves.

## Key Dependencies

- `chess`: PGN parsing and move validation
- `duckdb`: Local database storage
- `click`: CLI framework
