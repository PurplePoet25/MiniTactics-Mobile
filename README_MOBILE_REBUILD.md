# MiniTactics — Pocket Warboard Mobile Rebuild

This rebuild uses the real `minitactics_duel (2).zip` source and the supplied assets. No new image assets were added.

## What changed

- Converted the game shell to portrait mobile layout: 720×1280.
- Rebuilt the main UI around tap-first controls instead of desktop drag/double-click dependence.
- Added visible staged moments for game understanding:
  - Enemy turn announcement.
  - Enemy movement animation.
  - Incoming attack announcement.
  - Strike round explanation before strike resolves.
  - Corruption round explanation before corruption resolves.
  - Tornado announcement and visible piece shuffle.
  - Score announcement and burst animation.
- Reworked CPU turn execution so enemy actions are readable rather than instant/hidden.
- Kept the original 3×3 board, pieces, inventories, line scoring, strike/corrupt phases, shields, mage ward, soldier diagonal challenge, and duel minigame system.
- Patched two keyboard-only minigames for mobile touch:
  - `sudden_spark.py`: tap works like SPACE.
  - `guard_break.py`: tap works like SPACE.
- Removed `.venv` and `__pycache__` from the packaged build.

## Controls

- Tap a piece in **Your Hand**, then tap a free board tile to place it.
- Tap one of your board pieces to select it.
- Tap an adjacent tile to move or challenge an enemy.
- Tap **POWER** after selecting one of your pieces:
  - Mage: ward an empty tile from next Corrupt.
  - Shielder: shield self or adjacent ally.
  - Soldier: challenge a diagonal enemy.
- Tap **CANCEL** to clear selection.

## Run on desktop for preview

```bash
py -m pip install -r minitactics_duel/requirements.txt
py minitactics_duel/run_game.py
```

Or:

```bash
python minitactics_duel/run_game.py
```

## Note

I could statically compile-check the Python files, but this environment does not have `pygame` installed, so I could not perform a live runtime playtest here. The code is structured conservatively around the original files, but a real device/pygame test pass is still recommended before calling it final-final.
