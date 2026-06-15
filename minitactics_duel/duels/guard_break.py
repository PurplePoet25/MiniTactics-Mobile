# duels/guard_break.py
import os, math, random
from typing import Tuple
import pygame as pg

from config import asset, WIN_W, WIN_H, FPS, TEAL, RED, TEXT
from utils import load_img, draw_text

def _load_img(candidates, alpha=True) -> pg.Surface:
    """Try assets/minigames/<name> then bare <name>."""
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

# ----- Assets & sizing -------------------------------------------------------
_BG    = _load_img(["gb_bg.png", "gb_bg.p_.png"], alpha=False)
_BAR   = _load_img(["gb_bar.png", "gb_b_.png"])
_WIN   = _load_img(["gb_window_teal.png"])
_PUCK  = _load_img(["gb_puck.png", "gb_p_.png"])
_STRIP = _load_img(["gb_s_.png", "gb_shield_cracks_strip.png"])  # 1×3 sheet

_BG = pg.transform.smoothscale(_BG, (WIN_W, WIN_H))

# Stretch to fill the background's bar track nicely
BAR_W = int(WIN_W * 0.86)
BAR_H = 120                         # thicker bar (keep)
PUCK_SZ = (160, 160)                # big puck; clamped to inner rail (keep)
BAR    = pg.transform.scale(_BAR, (BAR_W, BAR_H))
PUCK   = pg.transform.scale(_PUCK, PUCK_SZ)
WINIMG = pg.transform.scale(_WIN, (220, BAR_H))  # base; we rescale width every frame

def _slice_cracks(sheet) -> Tuple[pg.Surface, pg.Surface, pg.Surface]:
    w, h = sheet.get_size()
    fw = w // 3
    frames = []
    for i in range(3):
        sub = sheet.subsurface(pg.Rect(i * fw, 0, fw, h)).copy()
        # smaller so it doesn’t cover the bar; we also draw it above the bar
        frames.append(pg.transform.scale(sub, (int(fw * 0.55), int(h * 0.55))))
    return tuple(frames)

CRACKS = _slice_cracks(_STRIP)

# ----- Game object -----------------------------------------------------------
class GuardBreak:
    """Parry timing: stop the puck within the teal window. Best-of-3."""
    def __init__(self, screen, difficulty="NORMAL"):
        self.screen = screen
        # Faster motion with higher difficulty
        if difficulty == "EASY":
            self.win_w, self.speed, self.cpu_sigma, self.cpu_early = 300, 8000.0, 0.085, 0.010
        elif difficulty == "HARD":
            self.win_w, self.speed, self.cpu_sigma, self.cpu_early = 200, 1500.0, 0.045, 0.006
        else:  # NORMAL
            self.win_w, self.speed, self.cpu_sigma, self.cpu_early = 240, 1200.0, 0.060, 0.008

    # ---------- intro & countdown ----------
    def intro(self):
        while True:
            self.screen.blit(_BG, (0, 0))
            draw_text(self.screen, "G U A R D   B R E A K", (WIN_W//2, 140), 40, TEXT, center=True)
            draw_text(self.screen, "Press SPACE when the moving puck is inside the teal window.",
                      (WIN_W//2, WIN_H//2 - 12), 26, TEXT, center=True)
            draw_text(self.screen, "Click or press any key to start",
                      (WIN_W//2, WIN_H//2 + 42), 22, TEAL, center=True)
            pg.display.flip()
            for e in pg.event.get():
                if e.type == pg.QUIT: return False
                if e.type in (pg.KEYDOWN, pg.MOUSEBUTTONDOWN): return True

    def countdown(self):
        for label, ms in [("3", 520), ("2", 520), ("1", 520), ("GO!", 560)]:
            self.screen.blit(_BG, (0, 0))
            draw_text(self.screen, "G U A R D   B R E A K", (WIN_W//2, 140), 40, TEXT, center=True)
            draw_text(self.screen, label, (WIN_W//2, WIN_H//2), 64 if label != "GO!" else 72, TEAL, center=True)
            pg.display.flip(); pg.time.wait(ms)
        pg.event.clear()

    # ---------- round setup ----------
    def _setup_round(self):
        self.cx, self.cy = WIN_W // 2, WIN_H // 2

        # bar rect (for drawing)
        self.bar_rect = BAR.get_rect(center=(self.cx, self.cy))
        self.bar_left = self.bar_rect.left

        # Symmetric inner rail (exclude rounded endcaps)
        ENDCAP_MARGIN = 0.90  # keep your current value
        self.inner_margin = int(BAR_H * ENDCAP_MARGIN)
        self.rail_left    = self.bar_rect.left  + self.inner_margin
        self.rail_right   = self.bar_rect.right - self.inner_margin
        self.rail_w       = self.rail_right - self.rail_left

        # Normalized position along rail and direction
        self.pos01 = random.random()
        self.dir   = 1 if random.random() < 0.5 else -1

        # Window normalized space, sized against the rail width
        pad01 = self.win_w / self.rail_w
        base  = random.uniform(0.10 + pad01/2, 0.90 - pad01/2)
        self.win_lo, self.win_hi = base - pad01/2, base + pad01/2

        # State
        self.player_pressed = self.cpu_pressed = False
        self.player_good = self.cpu_good = False

        # CPU target (slightly early in the direction of travel so it feels faster)
        target = (self.win_lo + self.win_hi) * 0.5 + random.gauss(0, self.cpu_sigma)
        early  = self.cpu_early if self.dir > 0 else -self.cpu_early
        target += early
        self.cpu_target = max(0.0, min(1.0, target))
        self.cpu_attempted = False

        # Feedback
        self.shake_time, self.shake_amt = 0.0, 0.0
        self.round_start = pg.time.get_ticks() / 1000.0

    def _in_window(self, x01: float) -> bool:
        return self.win_lo <= x01 <= self.win_hi

    def _to_inner_px(self, x01: float) -> float:
        """Map 0..1 to inner rail pixel coordinate (flat part of bar)."""
        return self.rail_left + x01 * self.rail_w

    def _puck_px(self) -> int:
        x = self._to_inner_px(self.pos01)
        half = PUCK_SZ[0] // 2
        x = max(self.rail_left + half, min(self.rail_right - half, x))
        return int(x)

    # ---------- main loop ----------
    def run(self):
        if not self.intro(): return "player"
        self.countdown()

        clock = pg.time.Clock()
        round_idx, you, cpu, cracks = 1, 0, 0, 0
        self._setup_round()

        while True:
            dt = clock.tick(FPS) / 1000.0
            now = pg.time.get_ticks() / 1000.0

            for e in pg.event.get():
                if e.type == pg.QUIT: return "player"
                if ((e.type == pg.KEYDOWN and e.key == pg.K_SPACE) or (e.type == pg.MOUSEBUTTONDOWN and e.button == 1)) and not self.player_pressed:
                    self.player_pressed = True
                    self.player_good = self._in_window(self.pos01)
                    if self.player_good:
                        you += 1
                        cracks = min(3, cracks + 1)
                        self.shake_time, self.shake_amt = 0.15, 6.0

            # Motion along the rail (normalized) — speed depends on difficulty
            self.pos01 += self.dir * (self.speed * dt) / self.rail_w
            if self.pos01 <= 0.0: self.pos01, self.dir = 0.0, 1
            elif self.pos01 >= 1.0: self.pos01, self.dir = 1.0, -1

            # CPU single attempt, slightly earlier than before
            if (not self.cpu_attempted) and (
                (self.dir > 0 and self.pos01 >= self.cpu_target) or
                (self.dir < 0 and self.pos01 <= self.cpu_target)
            ):
                self.cpu_attempted = True
                self.cpu_pressed = True
                guess = self.pos01 + random.uniform(-0.02, 0.02)
                self.cpu_good = self._in_window(guess)
                if self.cpu_good: cpu += 1

            end_round = (self.player_pressed and self.cpu_pressed) or (now - self.round_start > 3.3)

            self._draw(round_idx, you, cpu, cracks)

            if self.shake_time > 0.0:
                self.shake_time -= dt
                self.shake_amt = max(0.0, self.shake_amt - 40 * dt)

            if end_round:
                self._draw(round_idx, you, cpu, cracks); pg.display.flip(); pg.time.wait(280)
                round_idx += 1
                if round_idx > 3:
                    if you == cpu: return "tie"
                    return "player" if you > cpu else "cpu"
                self._setup_round()

    # ---------- rendering ----------
    def _draw(self, rnd, you, cpu, cracks):
        self.screen.blit(_BG, (0, 0))

        draw_text(self.screen, f"G U A R D   B R E A K — Round {rnd}/3",
                  (WIN_W//2, 88), 30, TEXT, center=True)
        draw_text(self.screen, f"YOU {you} | CPU {cpu}",
                  (WIN_W//2, WIN_H - 84), 26, TEXT, center=True)

        # bar (centered)
        self.bar_rect = BAR.get_rect(center=(WIN_W//2, WIN_H//2))
        self.screen.blit(BAR, self.bar_rect)

        # teal window — clamped to inner rail
        wl_px = self._to_inner_px(self.win_lo)
        wr_px = self._to_inner_px(self.win_hi)
        ww    = max(14, int(wr_px - wl_px))
        window = pg.transform.scale(WINIMG, (ww, BAR_H))

        shake_x = int(math.sin(pg.time.get_ticks() * 0.06) * self.shake_amt) if self.shake_time > 0.0 else 0
        self.screen.blit(window, window.get_rect(midleft=(int(wl_px) + shake_x, self.bar_rect.centery)))

        # puck — strictly inside inner rail (never leaves the bar)
        puck_y = self.bar_rect.centery
        self.screen.blit(PUCK, PUCK.get_rect(center=(self._puck_px(), puck_y)))

        # shield cracks smaller & above bar
        if cracks > 0:
            cf = CRACKS[min(cracks - 1, 2)]
            self.screen.blit(cf, cf.get_rect(center=(WIN_W//2, self.bar_rect.top - 110)))

        pg.display.flip()

# Public entry
def run_guard_break(screen, clock, difficulty="NORMAL"):
    return GuardBreak(screen, difficulty=difficulty).run()
