# MiniTactics Mobile — Quality Test Report

Release candidate: `MiniTactics_Pocket_Warboard_Mobile_FINAL.zip`

## What was checked

- Python syntax compile check for all core files and duel minigames.
- Pygame headless launch and UI render at 720×1280 portrait resolution.
- Main screen layout: header, board, event log, hand cards, power/cancel buttons.
- Board cell rectangles: all 9 hitboxes remain inside the board and do not overlap.
- Required assets: all board, tile, piece, effect, and minigame PNGs are present.
- Duel minigame smoke tests: Rune Weave, Guard Break, Skirmish Lanes, Arc Shot, and Sudden Spark all launched and returned a result under automated input.
- Gameplay simulation: repeated randomized legal turns with player actions, CPU actions, corruption, strike, scoring, captures, and movement invariants.

## Important fixes made in this final pass

- Fixed a scoring bug where tornado movement could accidentally break a newly formed line before the player received damage/scoring credit.
- CPU placements are now animated into the board instead of appearing instantly.
- Player placements are now animated into the board for clearer mobile feedback.
- HP display now uses drawn pips instead of text hearts, avoiding missing-symbol boxes on Android/Linux fonts.
- Selection highlights now draw under pieces instead of over them, so pieces remain readable.
- Strike and claim effects now clean themselves after their timers expire.
- Added a root `main.py`, `buildozer.spec`, and GitHub Actions APK workflow scaffold.

## Honest caveat

This was tested in a Linux/Pygame environment and with headless automated interaction. It was not physically tested on an Android phone inside this environment. The included GitHub Actions workflow is prepared for APK building, but the first Android build may still need dependency tweaks depending on current python-for-android / pygame-ce support.
