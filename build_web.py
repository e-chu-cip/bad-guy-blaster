"""Package only the game's source for the browser, excluding local private files."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile


def default_test_mode(project):
    """Use Cloudflare's branch name, or the checked-out branch for local builds."""
    branch = os.environ.get("CF_PAGES_BRANCH")
    if branch is None:
        try:
            branch = subprocess.run(
                ["git", "branch", "--show-current"], cwd=project,
                check=True, capture_output=True, text=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            branch = ""
    return branch == "experimental-gameplay"


def main():
    project = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-test-mode", action="store_true",
                        default=default_test_mode(project),
                        help="Keep Test Mode in a separate development browser build.")
    args = parser.parse_args()
    output = project / "build" / "web"
    output.parent.mkdir(exist_ok=True)

    # Pygbag packages its input folder. Include only the game and public settings.
    with tempfile.TemporaryDirectory(prefix="web-build-") as temporary:
        app = Path(temporary) / "bad-guy-blaster"
        app.mkdir()
        shutil.copy2(project / "main.py", app / "main.py")
        (app / "game_config.py").write_text(
            f"TEST_MODE_ENABLED = {args.include_test_mode!r}\n", encoding="utf-8"
        )
        subprocess.run(
            [sys.executable, "-m", "pygbag", "--build", "--no_opt",
             "--title", "Bad Guy Blasters", "--width", "1000", "--height", "700",
             str(app)],
            check=True,
        )
        built = app / "build" / "web"
        archives = list(built.glob("*.apk"))
        if len(archives) != 1:
            raise RuntimeError("Expected one packaged game archive.")
        with zipfile.ZipFile(archives[0]) as archive:
            if set(archive.namelist()) != {"assets/main.py", "assets/game_config.py"}:
                raise RuntimeError("Unexpected files in game archive; stopping publication.")
        shutil.copytree(built, output, dirs_exist_ok=True)

    print("Browser build ready in build/web")
    print("Preview: python -m http.server 8000 --bind 127.0.0.1 --directory build/web")


if __name__ == "__main__":
    main()
