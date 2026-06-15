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

## Release Candidate Patch — APK Build Stability

Additional scan after GitHub Actions failures:

- Fixed root `main.py` launcher import collision. The earlier launcher could import itself instead of `minitactics_duel/main.py` when run as Buildozer's app entry point.
- Changed `buildozer.spec` from `pygame-ce` to `pygame` for better python-for-android recipe compatibility.
- Reduced Android architecture target to `arm64-v8a` for a faster and more reliable first APK build. This supports modern Android phones including Pixel devices.
- Replaced the GitHub Actions workflow with a cleaner Java/Python/Buildozer setup.
- Added full Buildozer log artifact upload so hidden python-for-android errors can be downloaded if the APK build fails again.
- Added cache cleanup before build to prevent old `pygame-ce`/Buildozer state from leaking into new runs.

Caveat: this package has been compile-checked in the sandbox, but final Android runtime behavior still depends on the APK produced by GitHub Actions and should be tested on a real phone.
