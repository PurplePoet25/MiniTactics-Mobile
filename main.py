"""Buildozer/Android launcher for MiniTactics Pocket Warboard.

Buildozer may package source files as .pyc inside the APK. A file-path loader
that points at minitactics_duel/main.py can fail on Android when the .py file is
not present. Use normal module importing instead; Python can load the packaged
.pyc modules correctly.
"""
from __future__ import annotations

import importlib
import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.join(ROOT_DIR, "minitactics_duel")

# The original game modules use absolute imports like `from config import ...`.
# Put the game folder first so those imports resolve on desktop and Android.
if GAME_DIR not in sys.path:
    sys.path.insert(0, GAME_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def main() -> None:
    game_module = importlib.import_module("minitactics_duel.main")
    game_module.main()


if __name__ == "__main__":
    main()
