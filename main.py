"""Android/GitHub Actions launcher for MiniTactics Pocket Warboard.

This root-level launcher exists because Buildozer expects a ``main.py`` at
``source.dir``. The actual game lives in ``minitactics_duel/main.py``.

Do not use ``from main import main`` here: when this file is executed as the
root app entry point, Python may resolve ``main`` back to this same launcher.
We load the real game module from its file path instead.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
GAME_DIR = ROOT_DIR / "minitactics_duel"
GAME_MAIN = GAME_DIR / "main.py"

# The original MiniTactics source uses imports like ``from config import ...``.
# Keeping the game directory first preserves that existing logic unchanged.
if str(GAME_DIR) not in sys.path:
    sys.path.insert(0, str(GAME_DIR))


def _load_game_main():
    spec = importlib.util.spec_from_file_location("minitactics_duel_entry", GAME_MAIN)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load game entry point: {GAME_MAIN}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main


def main() -> None:
    _load_game_main()()


if __name__ == "__main__":
    main()
