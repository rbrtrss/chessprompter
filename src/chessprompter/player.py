"""Interactive game player for chessprompter."""

import sys
import tty
import termios


def get_single_key() -> str:
    """Read a single keypress from stdin."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def clear_line() -> None:
    """Clear the current line."""
    print("\r\033[K", end="", flush=True)


def play_game(
    white: str,
    black: str,
    year: int | None,
    event: str | None,
    result: str | None,
    moves: list[str],
) -> None:
    """Interactively play through a game move by move."""
    print("\n" + "=" * 60)
    print(f"  {white} vs {black}")
    if year:
        print(f"  Year: {year}")
    if event:
        print(f"  Event: {event}")
    if result:
        print(f"  Result: {result}")
    print("=" * 60)
    print("\nControls: [n]ext  [b]ack  [q]uit")
    print("-" * 40)

    current_move = 0
    total_moves = len(moves)

    def display_position() -> None:
        clear_line()
        if current_move == 0:
            print("\r  Starting position", end="", flush=True)
        else:
            move_num = (current_move + 1) // 2
            is_white = (current_move % 2) == 1
            # color = "White" if is_white else "Black"
            move_san = moves[current_move - 1]
            if is_white:
                print(f"\r {move_num}. {move_san} [{current_move}/{total_moves}]", end="", flush=True)
            else:
                print(f"\r {move_num}... {move_san} [{current_move}/{total_moves}]", end="", flush=True)
            # print(f"\r  Move {move_num}. {color}: {move_san}  [{current_move}/{total_moves}]", end="", flush=True)

    display_position()

    while True:
        key = get_single_key()

        if key in ("q", "Q", "\x03"):  # q, Q, or Ctrl+C
            print("\n")
            break
        elif key in ("n", "N", " "):  # n, N, or space
            if current_move < total_moves:
                current_move += 1
                display_position()
        elif key in ("b", "B"):  # b or B
            if current_move > 0:
                current_move -= 1
                display_position()
