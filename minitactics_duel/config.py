# config.py — Mobile-first settings for MiniTactics: Pocket Warboard

TITLE = "MiniTactics — Pocket Warboard Mobile"
WIDTH, HEIGHT = 720, 1280
WIN_W, WIN_H = WIDTH, HEIGHT
FPS = 60

# Grid geometry: 3x3 board, large enough for thumbs on portrait screens
GRID_SIZE = 3
CELL_SIZE = 214
CELL_PX = CELL_SIZE
GRID_PAD = 14
GRID_INSET = GRID_PAD
BOARD_PX = GRID_SIZE * CELL_PX
CELL_INNER = CELL_PX - 2 * GRID_INSET

PIECE_PX = 128
INV_PIECE_PX = 92
RING_PX = 140
CLAIM_SKULL_PX = 96
PANEL_W = 680
HEADER_H = 96
FOOTER_H = 150
PANEL_PAD = 18

# Colors
BG = (13, 15, 22)
SLATE = (18, 20, 28)
BOARD_BG = (22, 24, 34)
GRID_LINE = (70, 78, 96)
PLAYER_TINT = (32, 44, 52)
CPU_TINT = (48, 30, 30)
PLAYER_FILL = (52, 212, 230)
CPU_FILL = (232, 92, 92)
WHITE = (240, 244, 252)
MUTED = (155, 165, 188)
TEXT = WHITE
TEXT_DIM = (178, 188, 205)
ACCENT = (255, 177, 78)
ACCENT2 = (75, 210, 255)
ACCENT_WARM = ACCENT
ACCENT_DIM = (210, 151, 72)
WARN = (248, 186, 67)
CORRUPT = (168, 126, 218)
CARD_BG = (26, 29, 40)
CARD_STROKE = (80, 90, 110)
TEAL = (69, 231, 255)
RED = (236, 88, 88)

START_HP = 3
DUEL_TYPES = ["rune_weave", "guard_break", "skirmish_lanes", "arc_shot", "sudden_spark"]

ANIM = {
    "modal_fade": 160,
    "toast": 1050,
    "settle_small": 220,
    "piece_move": 420,
    "cpu_piece_move": 560,
    "claim_skull": 780,
    "strike_flash": 520,
    "pre_event": 900,
    "post_event": 520,
    "tornado_move": 680,
    "score_burst": 760,
}

CPU_THINK_MIN = 420
CPU_THINK_MAX = 760

HEART_FONT_CANDIDATES = [
    "Segoe UI Symbol", "Arial Unicode MS", "DejaVu Sans", "Noto Sans Symbols", "Arial",
]

import os

def asset(*parts):
    here = os.path.dirname(__file__)
    candidates = [
        os.path.join(here, "assets", "minigames", *parts),
        os.path.join(here, "assets", *parts),
        os.path.join(here, *parts),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return parts[-1] if parts else here
