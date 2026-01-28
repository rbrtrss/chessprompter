# chessprompter

chessprompter is a command line tool that shows the plays of a chess game sequentially. It is intended as a minimalistic aid tool for training with a physical board without distractions. Games are loaded in PGN format.

## Installation

```bash
pip install chessprompter
```

Or install from source:

```bash
git clone https://github.com/yourusername/chessprompter.git
cd chessprompter
pip install .
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
