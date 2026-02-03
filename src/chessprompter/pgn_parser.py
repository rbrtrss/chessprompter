"""PGN file parsing utilities."""

import re
import chess.pgn
from pathlib import Path
from typing import Iterator
from dataclasses import dataclass


def detect_consultation_players(name: str) -> list[str]:
    """Detect and split consultation players from a player name string.

    Splits on " and " or " & " patterns.
    Returns a list of individual player names.
    """
    pattern = r'\s+and\s+|\s*&\s*'
    players = re.split(pattern, name, flags=re.IGNORECASE)
    return [p.strip() for p in players if p.strip()]


@dataclass
class ParsedGame:
    """A parsed chess game."""

    white: str
    black: str
    white_players: list[str]
    black_players: list[str]
    is_consultation: bool
    year: int | None
    event: str | None
    result: str | None
    eco: str | None
    moves: list[str]


def parse_pgn_file(pgn_path: Path) -> Iterator[ParsedGame]:
    """Parse a PGN file and yield parsed games."""
    with open(pgn_path, encoding="utf-8", errors="replace") as pgn_file:
        while True:
            game = chess.pgn.read_game(pgn_file)
            if game is None:
                break

            headers = game.headers
            white = headers.get("White", "Unknown")
            black = headers.get("Black", "Unknown")

            date_str = headers.get("Date", "")
            year = None
            if date_str and date_str != "????.??.??":
                try:
                    year = int(date_str.split(".")[0])
                except (ValueError, IndexError):
                    pass

            event = headers.get("Event")
            if event == "?":
                event = None

            result = headers.get("Result")
            if result == "*":
                result = None

            eco = headers.get("ECO")
            if eco == "?":
                eco = None

            moves = []
            board = game.board()
            for move in game.mainline_moves():
                san = board.san(move)
                moves.append(san)
                board.push(move)

            white_players = detect_consultation_players(white)
            black_players = detect_consultation_players(black)
            is_consultation = len(white_players) > 1 or len(black_players) > 1

            yield ParsedGame(
                white=white,
                black=black,
                white_players=white_players,
                black_players=black_players,
                is_consultation=is_consultation,
                year=year,
                event=event,
                result=result,
                eco=eco,
                moves=moves,
            )
