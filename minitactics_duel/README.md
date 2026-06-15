
# MiniTactics: Duel Edition (Pygame)

A tiny 3×3 tactics duel where each contested tile launches a quick minigame. You both command three pieces—**Mage**, **Shielder**, **Soldier**—with simple moves and one‑tap powers. Between turns, the world throws in **Minions**, **Strikes**, and **Corruption**.

This scaffold implements:
- Board + sidebar (HP, turn number, "Computer is thinking..." text)
- Drag‑from‑inventory placement (mouse-first)
- Contest resolution via a duel simulator (visual minigames can be added)
- Director cycle after CPU turn: `place_minion → strike → corrupt`
- Corruption cleansed by Mage on placement; minion blocks until beaten
- Lines score 1 damage and **clear** (pieces return to inventory / powers reset on death)

**Assets:** All asset paths are built with Python's `os.path` from `config.asset()` — no pygame resource locators. You can swap the PNGs in `assets/` freely.

## Controls
- Drag a piece from the right inventory onto a grid cell to place.
- Hover a tile to see its duel icon type.
- The CPU "thinks" concurrently; if it finishes before you place, its piece pops instantly when you drop onto the grid.

## Run
```
pip install pygame
python main.py
```

## Files
```
config.py        # settings + asset path helper (uses os.path.join)
utils.py         # image/text helpers
pieces.py        # enums & per-piece state
board.py         # board cells, lines, corruption & clear
director.py      # Place Minion → Strike → Corrupt loop
duel_manager.py  # duel resolution (MVP: random with small bias hooks)
ui.py            # rendering, input, drag/drop, CPU think, turn loop
main.py          # entry point
assets/          # placeholder art (replace with your art)
```

## Next Steps
- Implement powers UI (double‑click piece on board to cast Guard/Skirmish; Mage "safe tile" or Corrupt tweak per spec).
- Add visual duel scenes for **Smash**, **QTE**, **Bullseye**, then **Maze/Coin**.
- Add movement (drag piece 1 orthogonally) & initiate duels on move per your rules.
- Telemetry popups: "Challenged!", countdown, result banner, then apply winner with skull overlay flash.
- Difficulty tuning and seeded layouts.
