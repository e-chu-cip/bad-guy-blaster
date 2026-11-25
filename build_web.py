"""Package only the game's source for the browser, excluding local private files."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile


def main():
    project = Path(__file__).resolve().parent
    output = project / "build" / "web"
    output.parent.mkdir(exist_ok=True)

    # Pygbag packages its input folder. Use a clean folder containing only the game.
    with tempfile.TemporaryDirectory(prefix="web-build-") as temporary:
        app = Path(temporary) / "bad-guy-blaster"
        app.mkdir()
        shutil.copy2(project / "main.py", app / "main.py")
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
            if set(archive.namelist()) != {"assets/main.py"}:
                raise RuntimeError("Unexpected files in game archive; stopping publication.")
        shutil.copytree(built, output, dirs_exist_ok=True)

    print("Browser build ready in build/web")
    print("Preview: python -m http.server 8000 --bind 127.0.0.1 --directory build/web")


if __name__ == "__main__":
    main()
