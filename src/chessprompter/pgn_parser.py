"""PGN file parsing utilities."""

import chess.pgn
from pathlib import Path
from typing import Iterator
from dataclasses import dataclass


@dataclass
class ParsedGame:
    """A parsed chess game."""

    white: str
    black: str
    year: int | None
    event: str | None
    result: str | None
    pgn: str
    moves: list[str]


def parse_pgn_file(pgn_path: Path) -> Iterator[ParsedGame]:
    """Parse a PGN file and yield parsed games."""
    with open(pgn_path) as pgn_file:
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

            moves = []
            board = game.board()
            for move in game.mainline_moves():
                san = board.san(move)
                moves.append(san)
                board.push(move)

            exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
            pgn_str = game.accept(exporter)

            yield ParsedGame(
                white=white,
                black=black,
                year=year,
                event=event,
                result=result,
                pgn=pgn_str,
                moves=moves,
            )
