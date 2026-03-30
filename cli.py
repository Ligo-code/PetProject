"""
Silicon Valley Trail — entry point.

Run with:
    python cli.py
"""

from silicon_valley_trail.models.game_state import GameState
from silicon_valley_trail.engine.game_loop import run_game
from silicon_valley_trail.storage import save_game, load_game, delete_save


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_choice(max_option: int) -> int:
    while True:
        try:
            raw = input(f"\nEnter choice (1-{max_option}): ").strip()
            value = int(raw)
            if 1 <= value <= max_option:
                return value
        except (ValueError, EOFError):
            pass
        print(f"Please enter a number between 1 and {max_option}.")


def _press_enter() -> None:
    try:
        input("\nPress Enter to continue...")
    except EOFError:
        pass


# ---------------------------------------------------------------------------
# Intro
# ---------------------------------------------------------------------------

def _show_intro() -> None:
    print()
    print("=" * 60)
    print("  SILICON VALLEY TRAIL")
    print("=" * 60)
    print()
    print("  Your scrappy startup team is heading from San Jose")
    print("  to San Francisco to pitch for Series A funding!")
    print()
    print("  Manage your resources wisely:")
    print("    Cash     — don't run out")
    print("    Morale   — keep the team happy")
    print("    Coffee   — essential fuel (2 days without = game over)")
    print("    Hype     — public interest in your startup")
    print("    Bugs     — keep them under control (20 = game over)")
    print()
    print("  Your team:")
    print("    Kay  [backend]  — core founder, never leaves")
    print("    Hanna [frontend] — design & UI, watch out for poaching")
    print("    Leo  [product]  — full-stack visionary, burns out if pushed")
    print()
    print("  Good luck, founder!")
    print("=" * 60)
    _press_enter()


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def _main_menu() -> None:
    while True:
        print()
        print("=" * 60)
        print("  SILICON VALLEY TRAIL")
        print("=" * 60)
        print("  1. New Game")
        print("  2. Load Game")
        print("  3. Quit")

        choice = _get_choice(3)

        if choice == 1:
            _show_intro()
            state = GameState()
            run_game(
                state,
                save_callback=save_game,
                quit_callback=lambda: None,
            )
            delete_save()

        elif choice == 2:
            state = load_game()
            if state is None:
                print("\nNo saved game found.")
                _press_enter()
                continue
            print("\nGame loaded successfully!")
            _press_enter()
            run_game(
                state,
                save_callback=save_game,
                quit_callback=lambda: None,
            )
            delete_save()

        elif choice == 3:
            print("\nSee you on the trail!\n")
            break


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _main_menu()
