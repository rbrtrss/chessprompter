"""Command-line interface for chessprompter."""

import click
from pathlib import Path

from .database import get_connection, init_db, insert_game, list_games, get_game
from .pgn_parser import parse_pgn_file
from .player import play_game


@click.group()
@click.option(
    "--db",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to the database file (default: ~/.chessprompter/games.duckdb)",
)
@click.pass_context
def main(ctx: click.Context, db: Path | None) -> None:
    """chessprompter - A minimalistic CLI for chess training.

    Load PGN files, list games, and step through moves on your physical board.
    """
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = db


@main.command()
@click.argument("pgn_files", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.pass_context
def load(ctx: click.Context, pgn_files: tuple[Path, ...]) -> None:
    """Load PGN files into the database."""
    if not pgn_files:
        click.echo("No PGN files specified.", err=True)
        return

    conn = get_connection(ctx.obj["db_path"])
    init_db(conn)

    total_loaded = 0
    for pgn_path in pgn_files:
        click.echo(f"Loading {pgn_path}...")
        count = 0
        for game in parse_pgn_file(pgn_path):
            insert_game(
                conn,
                white=game.white,
                black=game.black,
                year=game.year,
                event=game.event,
                result=game.result,
                pgn=game.pgn,
                moves=",".join(game.moves),
            )
            count += 1
        click.echo(f"  Loaded {count} game(s)")
        total_loaded += count

    conn.close()
    click.echo(f"Total: {total_loaded} game(s) loaded")


@main.command(name="list")
@click.pass_context
def list_cmd(ctx: click.Context) -> None:
    """List all loaded games."""
    conn = get_connection(ctx.obj["db_path"])
    init_db(conn)

    games = list_games(conn)
    conn.close()

    if not games:
        click.echo("No games loaded. Use 'chessprompter load <pgn_file>' to load games.")
        return

    click.echo(f"{'ID':<6} {'White':<20} {'Black':<20} {'Year':<6} {'Result':<10} {'Event'}")
    click.echo("-" * 90)
    for game_id, white, black, year, event, result in games:
        year_str = str(year) if year else "-"
        result_str = result if result else "-"
        event_str = (event[:25] + "...") if event and len(event) > 28 else (event or "-")
        click.echo(f"{game_id:<6} {white:<20} {black:<20} {year_str:<6} {result_str:<10} {event_str}")


@main.command()
@click.argument("game_id", type=int)
@click.pass_context
def play(ctx: click.Context, game_id: int) -> None:
    """Play through a game move by move.

    Use 'n' to go forward, 'b' to go back, 'q' to quit.
    """
    conn = get_connection(ctx.obj["db_path"])
    init_db(conn)

    game = get_game(conn, game_id)
    conn.close()

    if not game:
        click.echo(f"Game with ID {game_id} not found.", err=True)
        return

    game_id, white, black, year, event, result, pgn, moves_str = game
    moves = moves_str.split(",") if moves_str else []

    if not moves:
        click.echo("This game has no moves.", err=True)
        return

    play_game(white, black, year, event, result, moves)


if __name__ == "__main__":
    main()
