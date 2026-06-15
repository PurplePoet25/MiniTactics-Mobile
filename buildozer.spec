[app]
title = MiniTactics Pocket Warboard
package.name = minitacticspocketwarboard
package.domain = org.hasanbukhari
source.dir = .
source.include_exts = py,png,md,txt
source.exclude_dirs = __pycache__,.git,tests,.pytest_cache
version = 1.0.0
requirements = python3==3.11.6,pygame
orientation = portrait
fullscreen = 1
android.permissions = VIBRATE
android.api = 35
android.minapi = 23
android.archs = arm64-v8a
android.numeric_version = 1000000

[buildozer]
log_level = 2
warn_on_root = 1
