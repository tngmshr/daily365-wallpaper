"""Add the iPhone Shortcut image path and offline precache list to Flutter web."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "web"
SOURCE_WALLPAPERS = ROOT / "assets" / "wallpapers"


def main() -> None:
    if not (BUILD / "index.html").is_file():
        raise SystemExit("Run flutter build web before this packaging step.")

    public_wallpapers = BUILD / "wallpapers"
    if public_wallpapers.exists():
        shutil.rmtree(public_wallpapers)
    shutil.copytree(SOURCE_WALLPAPERS, public_wallpapers)
    (BUILD / ".nojekyll").write_text("", encoding="utf-8")

    files = []
    for path in sorted(BUILD.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(BUILD).as_posix()
        if relative in {"service-worker.js", "precache-manifest.json"}:
            continue
        if relative.startswith("wallpapers/") or relative.startswith("downloads/"):
            continue
        files.append("./" + relative)
    if "./" not in files:
        files.insert(0, "./")
    (BUILD / "precache-manifest.json").write_text(
        json.dumps({"files": files}, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"Prepared {len(files)} offline app files and {len(list(public_wallpapers.glob('*.jpg')))} Shortcut wallpapers.")


if __name__ == "__main__":
    main()
