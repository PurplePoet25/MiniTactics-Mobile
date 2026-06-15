# duels/sudden_spark.py
import os, math, random
import pygame as pg

from config import asset, WIN_W, WIN_H, FPS, TEAL, RED, TEXT
from utils  import load_img, draw_text

# ---------- helpers ----------
def _load_img(candidates, alpha=True):
    for name in candidates:
        full = asset("minigames", name)
        path = full if os.path.exists(full) else (name if os.path.exists(name) else None)
        if not path:
            continue
        surf = load_img(path)
        if not alpha and pg.get_init() and pg.display.get_surface() is not None:
            try: surf = surf.convert()
            except Exception: pass
        return surf
    raise FileNotFoundError(candidates)

# ---------- assets ----------
_BG   = _load_img(["ss_bg.png"], alpha=False)
_CORE = _load_img(["ss_core.png"])
_RING = _load_img(["ss_flash_ring.png"])
_STAR = _load_img(["ss_star_pop.png"])

BG = pg.transform.smoothscale(_BG, (WIN_W, WIN_H))
CENTER = (WIN_W // 2, WIN_H // 2)

# Sizes (framed nicely)
BASE       = int(min(WIN_W, WIN_H) * 0.42)  # emblem
RING_BASE  = int(BASE * 1.18)               # halo
STAR_BASE  = int(BASE * 0.70)

CORE0 = pg.transform.smoothscale(_CORE, (BASE, BASE))
RING0 = pg.transform.smoothscale(_RING, (RING_BASE, RING_BASE))
STAR0 = pg.transform.smoothscale(_STAR, (STAR_BASE, STAR_BASE))

TITLE_Y   = 84
SUB_Y     = 120 + 16     # for round/score line (kept below title)
HINT_Y    = WIN_H - 86
BANNER_Y  = WIN_H//2 + int(BASE*0.32)  # clear of emblem

class SuddenSpark:
    """
    Reaction duel — press SPACE after the flash. Early press is a loss.
    Best-of-3 rounds; returns 'player' | 'cpu'.
    """
    def __init__(self, screen, difficulty="NORMAL"):
        self.screen = screen

        # Difficulty tuning (approx human RT: ~180–250ms typical)
        if difficulty == "EASY":
            self.cpu_react_ms    = (240, 360)  # slower
            self.cpu_false_prob  = 0.16
            self.hesitate_prob   = 0.35
            self.hesitate_ms     = (70, 160)
            self.flash_delay_rng = (0.90, 1.60)
            self.spark_dur       = 0.38        # longer/clearer spark
            self.player_grace_ms = 60          # CPU locks out for these ms after flash
            self.tie_bias_ms     = 40          # player wins close calls within this margin
        elif difficulty == "HARD":
            self.cpu_react_ms    = (170, 235)  # sharper
            self.cpu_false_prob  = 0.07
            self.hesitate_prob   = 0.12
            self.hesitate_ms     = (30, 90)
            self.flash_delay_rng = (0.70, 1.30)
            self.spark_dur       = 0.26
            self.player_grace_ms = 10
            self.tie_bias_ms     = 5
        else:  # NORMAL
            self.cpu_react_ms    = (200, 300)
            self.cpu_false_prob  = 0.12
            self.hesitate_prob   = 0.22
            self.hesitate_ms     = (50, 120)
            self.flash_delay_rng = (0.80, 1.45)
            self.spark_dur       = 0.32
            self.player_grace_ms = 30
            self.tie_bias_ms     = 20

        # runtime visuals
        self.spark_t   = 0.0   # drives bloom/flash + contracting halo
        self.spark_len = self.spark_dur

    # ---------- intro & countdown ----------
    def intro(self):
        """Instructions + click to start (emblem visible here)."""
        while True:
            self._draw(show_emblem=True, flash=False, star_time=0.0)
            draw_text(self.screen, "S U D D E N   S P A R K", (WIN_W//2, TITLE_Y), 34, TEXT, center=True)
            draw_text(
                self.screen,
                "Press SPACE when the emblem flashes.\n"
                "If you press before the flash, you lose.",
                (WIN_W//2, CENTER[1] + BASE//2 + 40), 24, TEXT, center=True
            )
            draw_text(self.screen, "Click or press any key to start", (WIN_W//2, HINT_Y), 22, TEAL, center=True)
            pg.display.flip()
            for e in pg.event.get():
                if e.type == pg.QUIT: return False
                if e.type in (pg.KEYDOWN, pg.MOUSEBUTTONDOWN): return True

    def countdown(self, round_idx, p_pts, c_pts):
        """3-2-1-GO on background only (no emblem to block text)."""
        for label, ms in [("3", 520), ("2", 520), ("1", 520), ("GO!", 560)]:
            self._draw(show_emblem=False, flash=False, star_time=0.0)
            draw_text(self.screen, "S U D D E N   S P A R K", (WIN_W//2, TITLE_Y), 34, TEXT, center=True)
            draw_text(self.screen, f"Round {round_idx}/3   —   YOU {p_pts} | CPU {c_pts}",
                      (WIN_W//2, SUB_Y), 22, TEXT, center=True)
            draw_text(self.screen, label, (WIN_W//2, WIN_H//2), 72 if label != "GO!" else 78, TEAL, center=True)
            pg.display.flip()
            pg.time.wait(ms)
        pg.event.clear()

    # ---------- single round ----------
    def play_round(self):
        clock = pg.time.Clock()

        flash_delay = random.uniform(*self.flash_delay_rng)
        t0 = pg.time.get_ticks() / 1000.0

        flashed = False
        result = None
        star_t = 0.0

        player_pressed = False
        cpu_pressed = False
        t_player = None
        t_cpu = None

        cpu_press_at = None
        cpu_false_at = (t0 + random.uniform(0.20, max(0.21, flash_delay - 0.06))) \
                        if random.random() < self.cpu_false_prob else None

        while result is None:
            dt = clock.tick(FPS) / 1000.0
            now = pg.time.get_ticks() / 1000.0
            elapsed = now - t0

            if (not flashed) and (elapsed >= flash_delay):
                flashed = True
                self.spark_len = self.spark_dur
                self.spark_t   = self.spark_len
                rx = random.uniform(*self.cpu_react_ms) / 1000.0
                if random.random() < self.hesitate_prob:
                    rx += random.uniform(*self.hesitate_ms) / 1000.0
                rx = max(0.0, rx + random.gauss(0.0, 0.015))
                rx += (self.player_grace_ms / 1000.0)
                cpu_press_at = now + rx

            if (not flashed) and cpu_false_at and now >= cpu_false_at:
                result, star_t = "player", 0.35

            if flashed and (not cpu_pressed) and cpu_press_at and now >= cpu_press_at:
                cpu_pressed = True
                t_cpu = now

            for e in pg.event.get():
                if e.type == pg.QUIT: return "player"
                if ((e.type == pg.KEYDOWN and e.key == pg.K_SPACE) or (e.type == pg.MOUSEBUTTONDOWN and e.button == 1)) and result is None:
                    if not flashed:
                        result, star_t = "cpu", 0.35
                    else:
                        player_pressed = True
                        t_player = now

            if flashed and (player_pressed or cpu_pressed) and result is None:
                if player_pressed and not cpu_pressed:
                    result, star_t = "player", 0.35
                elif cpu_pressed and not player_pressed:
                    result, star_t = "cpu", 0.35
                else:
                    diff = (t_cpu - t_player) if (t_cpu is not None and t_player is not None) else 0.0
                    if diff >= 0.0 and diff <= (self.tie_bias_ms / 1000.0):
                        result, star_t = "player", 0.35
                    else:
                        result, star_t = ("player", 0.35) if t_player < t_cpu else ("cpu", 0.35)

            if self.spark_t > 0.0:
                self.spark_t = max(0.0, self.spark_t - dt)

            # frame
            self._draw(show_emblem=True, flash=flashed, star_time=star_t)
            # clean, non-overlapping HUD (title top; hint bottom while waiting)
            draw_text(self.screen, "S U D D E N   S P A R K", (WIN_W//2, TITLE_Y), 30, TEXT, center=True)
            if not flashed:
                draw_text(self.screen, "Press SPACE on the flash. Early = loss.", (WIN_W//2, HINT_Y), 22, TEXT, center=True)
            pg.display.flip()

        # short settle look
        for _ in range(12):
            self._draw(show_emblem=True, flash=True, star_time=0.0)
            draw_text(self.screen, "S U D D E N   S P A R K", (WIN_W//2, TITLE_Y), 30, TEXT, center=True)
            pg.display.flip()
            clock.tick(FPS)

        return result

    # ---------- 3-round game ----------
    def run(self):
        if not self.intro(): return "player"

        p_pts = c_pts = 0
        round_idx = 1

        while p_pts < 2 and c_pts < 2 and round_idx <= 3:
            self.countdown(round_idx, p_pts, c_pts)
            winner = self.play_round()
            if winner == "player": p_pts += 1
            elif winner == "cpu":  c_pts += 1
            round_idx += 1

        result = "player" if p_pts > c_pts else ("cpu" if c_pts > p_pts else "tie")

        # final banner (below center; nothing else drawn that could overlap)
        clock = pg.time.Clock()
        for _ in range(36):
            self._draw(show_emblem=True, flash=True, star_time=0.0)
            draw_text(self.screen, "S U D D E N   S P A R K", (WIN_W//2, TITLE_Y), 30, TEXT, center=True)
            draw_text(self.screen,
                      "YOU WIN!" if result=="player" else ("CPU WINS!" if result=="cpu" else "TIE"),
                      (WIN_W//2, BANNER_Y), 52, TEAL if result=="player" else (RED if result=="cpu" else TEXT),
                      center=True)
            draw_text(self.screen, f"Final: YOU {p_pts} | CPU {c_pts}",
                      (WIN_W//2, BANNER_Y + 44), 26, TEXT, center=True)
            pg.display.flip()
            clock.tick(FPS)

        return result

    # ---------- rendering (no text here to avoid overlaps) ----------
    def _draw(self, *, show_emblem=True, flash=False, star_time=0.0):
        self.screen.blit(BG, (0, 0))

        if show_emblem:
            p = 1.0 + (0.035 * math.sin(pg.time.get_ticks() * 0.008))
            core = pg.transform.smoothscale(CORE0, (int(CORE0.get_width()*p), int(CORE0.get_height()*p)))
            self.screen.blit(core, core.get_rect(center=CENTER))

            ring = RING0.copy()
            ring.set_alpha(255 if flash else (110 + int(70 * (math.sin(pg.time.get_ticks()*0.012)*0.5 + 0.5))))
            self.screen.blit(ring, ring.get_rect(center=CENTER))

            if self.spark_t > 0.0:
                k = self.spark_t / self.spark_len
                bloom_scale = 1.0 + (1.15 * k)
                bloom = pg.transform.smoothscale(
                    RING0, (int(RING0.get_width()*bloom_scale), int(RING0.get_height()*bloom_scale))
                )
                bloom.set_alpha(int(255 * k))
                self.screen.blit(bloom, bloom.get_rect(center=CENTER))

                contract_scale = 1.0 - (0.22 * (1.0 - k))
                inner = pg.transform.smoothscale(
                    RING0, (int(RING0.get_width()*contract_scale), int(RING0.get_height()*contract_scale))
                )
                inner.set_alpha(int(210 * k))
                self.screen.blit(inner, inner.get_rect(center=CENTER))

                overlay = pg.Surface((WIN_W, WIN_H), pg.SRCALPHA)
                overlay.fill((255, 255, 255, int(120 * k)))
                self.screen.blit(overlay, (0, 0))

        if star_time > 0.0:
            s = 1.0 + 0.45 * (star_time / 0.35)
            star = pg.transform.smoothscale(STAR0, (int(STAR0.get_width()*s), int(STAR0.get_height()*s)))
            self.screen.blit(star, star.get_rect(center=CENTER))

# Public entry
def run_sudden_spark(screen, clock, difficulty="NORMAL"):
    return SuddenSpark(screen, difficulty=difficulty).run()
