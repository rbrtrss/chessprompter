# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

chessprompter is a minimalistic CLI tool for training chess with a physical board. It displays chess game moves sequentially from PGN files, allowing users to follow along on their physical board without distractions.

## Plan Mode

- Make the plan extremely concise. Sacrifice grammar for the sake of concision.
- At the end of each plan, give me a list of unresolved questions to answer, if any.

## Development Rules

- **Always use `uv` for all Python operations.** Do not use pip, python, or other tools directly. Use `uv run`, `uv sync`, `uv add`, etc.

## Development Commands

```bash
# Sync dependencies
uv sync

# Run the CLI
uv run chessprompter load game.pgn     # Import PGN files into database
uv run chessprompter list              # List all loaded games
uv run chessprompter play <game_id>    # Step through a game move by move
```

## Architecture

The codebase follows a simple layered structure in `src/chessprompter/`:

- **cli.py**: Click-based CLI entry point. Defines commands (load, list, play) and orchestrates the other modules.
- **pgn_parser.py**: Parses PGN files using the `chess` library. Yields `ParsedGame` dataclass instances with extracted metadata and SAN move lists.
- **schema.py**: DDL definitions for the star schema database structure.
- **database.py**: DuckDB persistence layer using a star schema.
- **player.py**: Terminal-based interactive player. Uses raw terminal input (`tty`/`termios`) for single-keypress navigation through moves.

### Database Schema

Star schema stored in `~/.chessprompter/games.duckdb`. See [schema-diagram.md](schema-diagram.md) for ER diagram.

### Commit Guidelines
- Before commiting changes, **ALWAYS** use the @.claude/skills/generating-commit-messages skill to generate commit messages
