import sys


# Hello
if __name__ == "__main__":
    if "--cli" in sys.argv:
        from cli.cli import run

        run()
    elif "--tk" in sys.argv:
        from ui.app import run_ui

        run_ui()
    else:
        try:
            from ui.pygame_app import run_ui
        except ModuleNotFoundError as exc:
            missing = exc.name or "a dependency"
            print(f"Missing dependency: {missing}")
            print("Install dependencies with: py -m pip install -r requirements.txt")
            sys.exit(1)

        run_ui()
