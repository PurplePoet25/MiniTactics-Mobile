
# temp_minigame_tester.py
# Lightweight harness to run the new minigames in isolation.
# Place this file in the project root (next to run_game.py) and run:
#   python temp_minigame_tester.py
#
# Keys:
#   1 = Rune Weave
#   2 = Guard Break
#   3 = Skirmish Lanes
#   4 = Arc Shot
#   5 = Sudden Spark
#   F1/F2/F3 = Easy / Normal / Hard
#   R = Random minigame
#   ENTER / Click a button to start
#   ESC = Back to menu (while playing) or Quit (on menu)
#   Q = Quit

import sys
import traceback
import pygame as pg

# Absolute imports so this works when run as a script
from config import WIDTH, HEIGHT, FPS, TITLE, WHITE, TEXT, BG, ACCENT, ACCENT2
from utils import draw_text, rounded_rect

# Import duel entry points
from duels.rune_weave import run_rune_weave
from duels.guard_break import run_guard_break
from duels.skirmish_lanes import run_skirmish_lanes
from duels.arc_shot import run_arc_shot
from duels.sudden_spark import run_sudden_spark

DUELS = [
    ("Rune Weave",      run_rune_weave),
    ("Guard Break",     run_guard_break),
    ("Skirmish Lanes",  run_skirmish_lanes),
    ("Arc Shot",        run_arc_shot),
    ("Sudden Spark",    run_sudden_spark),
]

DIFFS = ["EASY", "NORMAL", "HARD"]

BTN_W, BTN_H, BTN_GAP = 360, 64, 16

def make_buttons(screen, labels):
    cx, cy = WIDTH // 2, HEIGHT // 2 + 40
    total_h = len(labels) * BTN_H + (len(labels) - 1) * BTN_GAP
    start_y = cy - total_h // 2
    rects = []
    for i, label in enumerate(labels):
        r = pg.Rect(cx - BTN_W // 2, start_y + i * (BTN_H + BTN_GAP), BTN_W, BTN_H)
        rects.append((r, label))
    return rects

def draw_menu(screen, selected_idx, diff_idx, btns):
    screen.fill(BG)
    draw_text(screen, "MiniTactics — Minigame Tester", (WIDTH//2, 120), 40, WHITE, center=True)
    draw_text(screen, "Pick a minigame (1–5) • F1/F2/F3 = Easy/Normal/Hard • ENTER/Click to run • R=Random", 
              (WIDTH//2, 170), 22, TEXT, center=True)

    # Difficulty pill
    pill = pg.Rect(WIDTH//2 - 100, 200, 200, 36)
    rounded_rect(screen, pill, (28, 33, 44), radius=18, stroke_w=2, stroke_color=(80, 90, 110))
    draw_text(screen, f"Difficulty: {DIFFS[diff_idx]}", pill.center, 22, ACCENT2, center=True)

    # Buttons
    mx, my = pg.mouse.get_pos()
    for i, (rect, label) in enumerate(btns):
        hover = rect.collidepoint(mx, my)
        fill = (32, 36, 48) if not hover else (38, 42, 58)
        stroke = ACCENT if i == selected_idx else (80, 90, 110)
        rounded_rect(screen, rect, fill, radius=12, stroke_w=2, stroke_color=stroke)
        draw_text(screen, f"{i+1}. {label}", rect.center, 26, WHITE, center=True)

    pg.display.flip()

def run_duel(screen, clock, duel_idx, diff_idx):
    name, func = DUELS[duel_idx]
    # pre-banner
    screen.fill(BG)
    draw_text(screen, f"{name}", (WIDTH//2, HEIGHT//2 - 12), 40, WHITE, center=True)
    draw_text(screen, f"Difficulty: {DIFFS[diff_idx]}", (WIDTH//2, HEIGHT//2 + 36), 24, ACCENT2, center=True)
    draw_text(screen, "Press ESC to cancel", (WIDTH//2, HEIGHT - 80), 20, TEXT, center=True)
    pg.display.flip()
    pg.time.wait(360)

    # Run the duel. Each duel returns: "player" | "cpu" | "tie"
    try:
        result = func(screen, clock, difficulty=DIFFS[diff_idx])
    except SystemExit:
        raise
    except Exception:
        # Show a readable error screen instead of crashing.
        err = traceback.format_exc()
        show_error(screen, err)
        return None

    # Post-result banner
    if result:
        color = (140, 200, 255) if result == "player" else ((255, 130, 130) if result == "cpu" else WHITE)
        screen.fill(BG)
        draw_text(screen, f"{name} — Result: {result.upper()}", (WIDTH//2, HEIGHT//2 - 8), 38, color, center=True)
        draw_text(screen, "Press any key or click to return to menu", (WIDTH//2, HEIGHT//2 + 44), 22, TEXT, center=True)
        pg.display.flip()
        wait_for_click_or_key()

def wait_for_click_or_key():
    while True:
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit(); sys.exit(0)
            if e.type in (pg.KEYDOWN, pg.MOUSEBUTTONDOWN):
                return
        pg.time.wait(10)

def show_error(screen, text):
    screen.fill((23, 16, 18))
    draw_text(screen, "Exception in minigame:", (WIDTH//2, 80), 28, (255, 180, 160), center=True)
    # Soft wrapped error text
    font = pg.font.SysFont(None, 20)
    lines = []
    for raw in text.splitlines():
        # primitive wrap
        while len(raw) > 90:
            cut = raw.rfind(" ", 0, 90)
            cut = cut if cut != -1 else 90
            lines.append(raw[:cut]); raw = raw[cut:].lstrip()
        lines.append(raw)

    y = 120
    for ln in lines[-28:]:  # limit onscreen
        img = font.render(ln, True, (255, 210, 200))
        screen.blit(img, (40, y))
        y += 22
        if y > HEIGHT - 40: break

    draw_text(screen, "Press any key to return to menu", (WIDTH//2, HEIGHT - 32), 22, (255, 210, 200), center=True)
    pg.display.flip()
    wait_for_click_or_key()

def main():
    pg.init()
    pg.display.set_caption(f"{TITLE} — Minigame Tester")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    clock  = pg.time.Clock()

    selected = 0
    diff_idx = 1  # NORMAL
    btns = make_buttons(screen, [name for name, _ in DUELS])

    # optional: launch a specific minigame via CLI (1-5)
    if len(sys.argv) >= 2:
        try:
            n = int(sys.argv[1]) - 1
            if 0 <= n < len(DUELS):
                run_duel(screen, clock, n, diff_idx)
        except Exception:
            pass

    running = True
    while running:
        draw_menu(screen, selected, diff_idx, btns)
        for e in pg.event.get():
            if e.type == pg.QUIT:
                running = False
            elif e.type == pg.KEYDOWN:
                if e.key in (pg.K_ESCAPE, pg.K_q):
                    running = False
                elif e.key == pg.K_F1:
                    diff_idx = 0
                elif e.key == pg.K_F2:
                    diff_idx = 1
                elif e.key == pg.K_F3:
                    diff_idx = 2
                elif e.key in (pg.K_1, pg.K_KP1):
                    selected = 0; run_duel(screen, clock, selected, diff_idx)
                elif e.key in (pg.K_2, pg.K_KP2):
                    selected = 1; run_duel(screen, clock, selected, diff_idx)
                elif e.key in (pg.K_3, pg.K_KP3):
                    selected = 2; run_duel(screen, clock, selected, diff_idx)
                elif e.key in (pg.K_4, pg.K_KP4):
                    selected = 3; run_duel(screen, clock, selected, diff_idx)
                elif e.key in (pg.K_5, pg.K_KP5):
                    selected = 4; run_duel(screen, clock, selected, diff_idx)
                elif e.key in (pg.K_r,):
                    # random
                    import random
                    selected = random.randrange(len(DUELS))
                    run_duel(screen, clock, selected, diff_idx)
                elif e.key in (pg.K_RETURN, pg.K_KP_ENTER, pg.K_SPACE):
                    run_duel(screen, clock, selected, diff_idx)
            elif e.type == pg.MOUSEBUTTONDOWN and e.button == 1:
                for i, (rect, _) in enumerate(btns):
                    if rect.collidepoint(e.pos):
                        selected = i
                        run_duel(screen, clock, selected, diff_idx)
                        break
            elif e.type == pg.MOUSEMOTION:
                for i, (rect, _) in enumerate(btns):
                    if rect.collidepoint(e.pos):
                        selected = i
                        break

        clock.tick(FPS)

    pg.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()
