# duels/rune_weave.py
import os, random
from math import sin, pi
import pygame as pg

from config import asset, WIN_W, WIN_H, FPS, TEAL, RED, TEXT
from utils import load_img, draw_text

# ---------- helpers / loading ----------
def _load_img(candidates, alpha=True):
    for name in candidates:
        full = asset("minigames", name)
        path = full if os.path.exists(full) else (name if os.path.exists(name) else None)
        if not path:
            continue
        surf = load_img(path)
        if not alpha and pg.get_init() and pg.display.get_surface() is not None:
            try:
                surf = surf.convert()
            except Exception:
                pass
        return surf
    raise FileNotFoundError(candidates)

def _scale_nn(surf, w, h):
    return pg.transform.scale(surf, (int(w), int(h)))

# ---------- art ----------
_BG         = _load_img(["rw_bg.png"], alpha=False)
_SLOT_EMPTY = _load_img(["rw_slot_empty.png"])
_FILL_TEAL  = _load_img(["rw_slot_fill_teal.png", "rw_slo_.png"])
_FILL_RED   = _load_img(["rw_slot_fill_red.png"])
_RING       = _load_img(["rw_focus_ring.png"])
_BURST      = _load_img(["rw_feedback_spark.png"])
try:
    _STICKER = _load_img(["rw_rune_sticker.png"])
except Exception:
    _STICKER = None

# Letters only
LETTER_POOL = [c for c in "ASDFJKLQWERTYUIOPHGNMZXCVB"]

# ---------- game ----------
def run_rune_weave(screen, clock, steps=4, difficulty="NORMAL"):
    """
    Rune Weave — type the shown letters in order. First to `steps` wins.
    Returns: "player" | "cpu" | "tie"
    """

    # layout/scales
    SLOT        = 188
    CENTER_SLOT = 228   # new: big backdrop coin behind the center key
    RING        = 264
    BURST       = 234
    STICK       = 96

    slot_empty   = _scale_nn(_SLOT_EMPTY, SLOT, SLOT)
    center_slot  = _scale_nn(_SLOT_EMPTY, CENTER_SLOT, CENTER_SLOT)
    fill_teal    = _scale_nn(_FILL_TEAL,  SLOT, SLOT)
    fill_red     = _scale_nn(_FILL_RED,   SLOT, SLOT)
    focus_ring   = _scale_nn(_RING,       RING, RING)
    burst        = _scale_nn(_BURST,      BURST, BURST)
    sticker      = _scale_nn(_STICKER,    STICK, STICK) if _STICKER else None
    bg_scaled    = pg.transform.smoothscale(_BG, (WIN_W, WIN_H))

    # sequence (letters only)
    seq = [(ch, getattr(pg, f"K_{ch.lower()}")) for ch in random.choices(LETTER_POOL, k=steps)]
    p_idx = c_idx = 0

    # ---------- title/help (click to start) ----------
    pg.event.clear()
    waiting = True
    while waiting:
        for ev in pg.event.get():
            if ev.type == pg.QUIT: return "player"
            if ev.type in (pg.MOUSEBUTTONDOWN, pg.KEYDOWN): waiting = False
        screen.blit(bg_scaled, (0, 0))
        draw_text(screen, "R U N E   W E A V E", (WIN_W//2, 110), 40, TEXT, center=True)
        draw_text(screen, "Press the letters in order. First to 4 wins.", (WIN_W//2, WIN_H//2+52), 22, TEXT, center=True)
        draw_text(screen, "Click to start", (WIN_W//2, WIN_H//2-4), 32, TEAL, center=True)
        pg.display.flip()
        clock.tick(60)

    # ---------- slower 1..5 countdown ----------
    for num in ["1","2","3","4","5"]:
        screen.blit(bg_scaled,(0,0))
        draw_text(screen, "R U N E   W E A V E", (WIN_W//2, 110), 36, TEXT, center=True)
        draw_text(screen, num, (WIN_W//2, WIN_H//2), 72, TEAL, center=True)
        pg.display.flip()
        pg.time.wait(520)

    pg.event.clear()

    # ---------- CPU timing (faster than before, still human) ----------
    if difficulty == "EASY":
        base_min, base_max = 620, 880
        accuracy = 0.86
        hesitate_p, hes_min, hes_max = 0.14, 180, 320
    elif difficulty == "HARD":
        base_min, base_max = 480, 720
        accuracy = 0.93
        hesitate_p, hes_min, hes_max = 0.10, 140, 260
    else:  # NORMAL
        base_min, base_max = 540, 780   # ← faster than previous version
        accuracy = 0.90
        hesitate_p, hes_min, hes_max = 0.12, 160, 300

    def next_cpu_time(now):
        delay = random.randint(base_min, base_max)
        if random.random() < hesitate_p:
            delay += random.randint(hes_min, hes_max)
        return now + delay

    now = pg.time.get_ticks()
    next_cpu = next_cpu_time(now)

    bursts = []

    # roomy layout to avoid overlaps
    cx = WIN_W//2
    spacing = 110
    slot_w = SLOT
    total_w = steps*slot_w + (steps-1)*spacing
    first_x = cx - total_w//2 + slot_w//2
    top_y, bottom_y = WIN_H//2 - 170, WIN_H//2 + 170

    def slot_center(i, row_y):
        return (first_x + i*(slot_w + spacing), row_y)

    def draw_row(progress, row_y, player=False):
        for i in range(steps):
            rect = slot_empty.get_rect(center=(int(first_x + i*(slot_w + spacing)), int(row_y)))
            screen.blit(slot_empty, rect)
            if i < progress:
                screen.blit(fill_teal if player else fill_red, rect)

    def add_burst(center, tint_color):
        bursts.append((pg.Vector2(center), pg.time.get_ticks()+160, tint_color))

    def draw_key_chip(label, center):
        # big center slot behind the key
        slot = center_slot.copy()
        slot.set_alpha(210)
        screen.blit(slot, slot.get_rect(center=center))
        # ring pulse + sticker + letter
        t = pg.time.get_ticks()/1000.0
        ring = focus_ring.copy()
        ring.set_alpha(180 + int(60*(0.5+0.5*sin(t*2*pi*0.7))))
        screen.blit(ring, ring.get_rect(center=center))
        if sticker:
            s = sticker.copy(); s.set_alpha(210)
            screen.blit(s, s.get_rect(center=(center[0], center[1]-4)))
        draw_text(screen, label, center, 96, TEXT, center=True)

    # ---------- main loop ----------
    winner = None
    while not winner:
        dt = clock.tick(FPS)/1000.0
        now = pg.time.get_ticks()

        for ev in pg.event.get():
            if ev.type == pg.QUIT: return "player"
            if ev.type == pg.KEYDOWN and p_idx < steps:
                if ev.key == seq[p_idx][1]:
                    add_burst(slot_center(p_idx, bottom_y), TEAL)
                    p_idx += 1

        if c_idx < steps and now >= next_cpu:
            if random.random() <= accuracy:
                add_burst(slot_center(c_idx, top_y), RED)
                c_idx += 1
            next_cpu = next_cpu_time(now)

        if p_idx >= steps and c_idx >= steps: winner = "tie"
        elif p_idx >= steps:                   winner = "player"
        elif c_idx >= steps:                   winner = "cpu"

        # draw
        screen.blit(bg_scaled,(0,0))
        draw_text(screen, "R U N E   W E A V E", (WIN_W//2, 84), 28, TEXT, center=True)
        draw_text(screen, f"You {p_idx}/{steps}   |   CPU {c_idx}/{steps}",
                  (WIN_W//2, WIN_H-72), 24, TEXT, center=True)

        draw_row(c_idx, top_y,    player=False)
        draw_row(p_idx, bottom_y, player=True)
        draw_key_chip(seq[min(p_idx, steps-1)][0], (WIN_W//2, WIN_H//2))

        # bursts
        for b in list(bursts):
            pos, until, color = b
            if now >= until:
                bursts.remove(b); continue
            spr = burst.copy()
            spr.set_alpha(int(255 * (until-now)/160))
            tint = pg.Surface(spr.get_size(), pg.SRCALPHA); tint.fill((*color,0))
            spr.blit(tint,(0,0), special_flags=pg.BLEND_RGBA_ADD)
            screen.blit(spr, spr.get_rect(center=(int(pos.x), int(pos.y))))

        pg.display.flip()

    # settle screen
    for _ in range(30):
        screen.blit(bg_scaled,(0,0))
        draw_row(c_idx, top_y, player=False); draw_row(p_idx, bottom_y, player=True)
        end_txt = "You win!" if winner=="player" else ("CPU wins!" if winner=="cpu" else "Tie!")
        draw_text(screen, end_txt, (WIN_W//2, WIN_H//2), 52,
                  TEAL if winner=="player" else (RED if winner=="cpu" else TEXT), center=True)
        pg.display.flip(); clock.tick(FPS)

    return winner
