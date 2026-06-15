"""Android/GitHub Actions launcher for MiniTactics."""
from pathlib import Path
import sys

GAME_DIR = Path(__file__).resolve().parent / "minitactics_duel"
sys.path.insert(0, str(GAME_DIR))

from main import main  # type: ignore  # imports minitactics_duel/main.py via sys.path

if __name__ == "__main__":
    main()
