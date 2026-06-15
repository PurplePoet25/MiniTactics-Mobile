# duels/skirmish_lanes.py  — First to 10 points
import os, random
from dataclasses import dataclass
import pygame as pg

from config import asset, WIN_W, WIN_H, FPS, TEAL, RED, TEXT
from utils  import load_img, draw_text, clamp

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
BG_IMG   = _load_img(["sl_bg.png"], alpha=False)
RUN_P    = _load_img(["sl_runner_teal.png"])
RUN_C    = _load_img(["sl_runner_red.png"])
BANNER_P = _load_img(["sl_banner_teal.png"])
BANNER_C = _load_img(["sl_banner_red.png"])
HAZARD   = _load_img(["sl_hazard_spark.png"])
FLASH    = _load_img(["sl_lane_flash.png"])
STARS_RAW= _load_img(["sl_stun_stars.png"])  # single-frame star

BG_IMG = pg.transform.smoothscale(BG_IMG, (WIN_W, WIN_H))

# ---------- layout & sizing ----------
LANES_Y = [int(WIN_H*(1/6)), int(WIN_H*(3/6)), int(WIN_H*(5/6))]

def _scale_by_h(img, h):
    w = int(img.get_width() * (h / img.get_height()))
    return pg.transform.smoothscale(img, (w, int(h)))

RUN_H = 240
RUN_P = _scale_by_h(RUN_P, RUN_H)
RUN_C = _scale_by_h(RUN_C, RUN_H)

TOKEN = 132               # banners bigger
HAZ   = 112               # hazard
BANNER_P = pg.transform.smoothscale(BANNER_P, (TOKEN, TOKEN))
BANNER_C = pg.transform.smoothscale(BANNER_C, (TOKEN, TOKEN))
HAZARD   = pg.transform.smoothscale(HAZARD,   (HAZ,   HAZ))

# stars: scaled relative to runner width, so it sits right on top of head
STAR_W = int(RUN_P.get_width() * 0.42)
STAR_H = int(STAR_W * (STARS_RAW.get_height() / STARS_RAW.get_width()))
STARS  = pg.transform.smoothscale(STARS_RAW, (STAR_W, STAR_H))

PLAYER_X, CPU_X = 260, WIN_W - 260

# pacing & spacing (fewer tokens)
ITEM_SPEED      = 360.0
STUN_TIME       = 1.00
BEAT            = 0.95                 # slower global cadence → fewer items
LANE_MIN_GAP    = 1.25                 # min seconds before same lane can spawn again
JITTER          = 0.10                 # small timing wobble

# spawn distribution targets (per item)
P_BLUE   = 0.30
P_RED    = 0.30
P_HAZ    = 0.30
P_NONE   = 0.10

TARGET_SCORE    = 10                   # <<< first to 10

COLLIDE_R = int(TOKEN * 0.38)

@dataclass
class Runner:
    x: int
    lane: int
    stunned_until: float = 0.0

@dataclass
class Item:
    kind: str  # "BP" | "BC" | "HZ"
    x: float
    lane: int
    dir: int
    life: float = 12.0

class SkirmishLanes:
    """
    You = teal. CPU = red. First to 10 points wins.
    Collect YOUR banners, avoid hazards. W/S or UP/DOWN to switch lanes.
    """
    def __init__(self, screen, difficulty="NORMAL"):
        self.screen = screen
        # Clear difficulty progression: EASY < NORMAL < HARD
        if difficulty == "EASY":
            self.cpu_react   = (0.40, 0.52)  # slow reactions
            self.cpu_miss    = 0.35          # frequent mistakes
            self.lookahead   = 180           # short look-ahead window (px)
            self.prefer_own  = 0.45          # weak preference for own banners
            self.dodge_skill = 0.45          # often fails to dodge hazards
            self.mimic_prob  = 0.30          # copies player a fair bit (derpy)
        elif difficulty == "HARD":
            self.cpu_react   = (0.14, 0.22)  # fast reactions
            self.cpu_miss    = 0.06          # rare mistakes
            self.lookahead   = 420           # long look-ahead window
            self.prefer_own  = 0.90          # aggressively prioritizes own banners
            self.dodge_skill = 0.92          # almost always dodges hazards
            self.mimic_prob  = 0.08          # mostly independent (smarter)
        else:  # NORMAL
            self.cpu_react   = (0.26, 0.34)  # moderate reactions
            self.cpu_miss    = 0.20          # some mistakes
            self.lookahead   = 280
            self.prefer_own  = 0.70
            self.dodge_skill = 0.72
            self.mimic_prob  = 0.16


    # ---------- intro / countdown ----------
    def intro(self):
        while True:
            self.screen.blit(BG_IMG, (0, 0))
            draw_text(self.screen, "S K I R M I S H   L A N E S", (WIN_W//2, 120), 38, TEXT, center=True)
            draw_text(self.screen, "W / S (or UP / DOWN) to change lanes.",
                      (WIN_W//2, WIN_H//2 - 30), 26, TEXT, center=True)
            draw_text(self.screen, f"First to {TARGET_SCORE} points. TEAL collects TEAL, RED collects RED. Hazards stun.",
                      (WIN_W//2, WIN_H//2 + 6), 24, TEXT, center=True)
            draw_text(self.screen, "Click or press any key to start",
                      (WIN_W//2, WIN_H//2 + 48), 22, TEAL, center=True)
            pg.display.flip()
            for e in pg.event.get():
                if e.type == pg.QUIT: return False
                if e.type in (pg.KEYDOWN, pg.MOUSEBUTTONDOWN): return True

    def countdown(self):
        for label, ms in [("3", 520), ("2", 520), ("1", 520), ("GO!", 560)]:
            self.screen.blit(BG_IMG, (0, 0))
            draw_text(self.screen, "S K I R M I S H   L A N E S", (WIN_W//2, 120), 38, TEXT, center=True)
            draw_text(self.screen, label, (WIN_W//2, WIN_H//2), 64 if label != "GO!" else 72, TEAL, center=True)
            pg.display.flip(); pg.time.wait(ms)
        pg.event.clear()

    # ---------- spawning ----------
    def _biased_choice(self):
        """Sample kind with 30/30/30/10 but nudge toward underrepresented banner color."""
        diff = self.blue_count - self.red_count  # positive ⇒ too many blue so far
        w_blue = P_BLUE * (0.75 if diff > 0 else (1.25 if diff < 0 else 1.0))
        w_red  = P_RED  * (1.25 if diff > 0 else (0.75 if diff < 0 else 1.0))
        w_hz   = P_HAZ
        w_none = P_NONE
        total  = w_blue + w_red + w_hz + w_none
        r = random.random() * total
        if r < w_blue:   return "BP"
        r -= w_blue
        if r < w_red:    return "BC"
        r -= w_red
        if r < w_hz:     return "HZ"
        return "NONE"

    def _spawn_tick(self):
        # choose a lane that respects per-lane spacing
        for _ in range(6):
            lane = random.randint(0, 2)
            if self.t - self.last_lane_spawn[lane] >= LANE_MIN_GAP:
                break
        else:
            return  # no lane available; skip this beat

        # Choose kinds for both directions independently with bias correction.
        kind_right = self._biased_choice()  # item moving right (+1) from left (CPU side)
        kind_left  = self._biased_choice()  # item moving left  (-1) from right (Player side)

        # apply “none” chance (fewer tokens overall)
        def push(kind, dir_sign):
            if kind == "NONE": return
            x0 = -80 if dir_sign > 0 else WIN_W + 80
            self.items.append(Item(kind, x0, lane, dir_sign))

        push(kind_right, +1)
        push(kind_left,  -1)

        # Update counts for balance statistics
        if kind_right == "BC": self.red_count  += 1
        if kind_left  == "BC": self.red_count  += 1
        if kind_right == "BP": self.blue_count += 1
        if kind_left  == "BP": self.blue_count += 1

        # lane flash cue
        self.flash_events.append((pg.time.get_ticks(), lane))
        self.last_lane_spawn[lane] = self.t

    # ---------- main ----------
    def run(self):
        if not self.intro(): return "player"
        self.countdown()

        clock = pg.time.Clock()
        self.p = Runner(PLAYER_X, 1)
        self.c = Runner(CPU_X, 1)
        self.items, self.flash_events = [], []
        self.p_score = self.c_score = 0
        self.t = 0.0
        start_ms = pg.time.get_ticks()

        self.next_spawn = BEAT + random.uniform(-JITTER, JITTER)
        self.last_lane_spawn = {0: -99.0, 1: -99.0, 2: -99.0}
        self.blue_count = 0
        self.red_count  = 0

        cpu_next_time  = 0.0
        cpu_delay      = random.uniform(*self.cpu_react)

        winner = None
        while winner is None:
            dt = clock.tick(FPS) / 1000.0
            self.t = (pg.time.get_ticks() - start_ms) / 1000.0

            # Player input
            for e in pg.event.get():
                if e.type == pg.QUIT: return "player"
                if e.type == pg.KEYDOWN and self.t >= self.p.stunned_until:
                    if e.key in (pg.K_w, pg.K_UP):   self.p.lane = max(0, self.p.lane-1)
                    if e.key in (pg.K_s, pg.K_DOWN): self.p.lane = min(2, self.p.lane+1)

            # Spawns (uniform beat)
            self.next_spawn -= dt
            if self.next_spawn <= 0:
                self._spawn_tick()
                self.next_spawn = BEAT + random.uniform(-JITTER, JITTER)

            # Item motion
            for it in list(self.items):
                it.x += it.dir * ITEM_SPEED * dt
                it.life -= dt
                if it.x < -200 or it.x > WIN_W+200 or it.life <= 0:
                    self.items.remove(it)

            # CPU behavior — difficulty-aware
            if self.t >= cpu_next_time:
                cpu_next_time = self.t + cpu_delay
                ahead = [i for i in self.items if i.dir == +1 and i.x <= self.c.x + self.lookahead]

                target = None
                # Prefer its own banner with difficulty-scaled likelihood
                if random.random() < self.prefer_own:
                    for i in sorted(ahead, key=lambda k: abs(self.c.x - k.x)):
                        if i.kind == "BC":
                            target = i
                            break

                if target:
                    target_lane = target.lane
                else:
                    # Hazard dodge with skill-based chance; otherwise maybe mimic player
                    hz = [i for i in ahead if i.kind=="HZ" and i.lane==self.c.lane and abs(i.x-self.c.x) < 150]
                    if hz and random.random() < self.dodge_skill:
                        target_lane = clamp(self.c.lane + random.choice([-1, 1]), 0, 2)
                    else:
                        target_lane = self.p.lane if random.random() < self.mimic_prob else self.c.lane

                if random.random() > self.cpu_miss and self.t >= self.c.stunned_until:
                    if   target_lane < self.c.lane: self.c.lane -= 1
                    elif target_lane > self.c.lane: self.c.lane += 1

                # Refresh delay window each tick for a bit of natural jitter
                cpu_delay = random.uniform(*self.cpu_react)

            # Collisions (check both sides first, then award to allow “simultaneous”)
            def collide(r, it): return abs(it.x - r.x) < COLLIDE_R and r.lane == it.lane

            p_gain = 0
            c_gain = 0
            stunned_p = False
            stunned_c = False

            for it in list(self.items):
                hit_p = collide(self.p, it)
                hit_c = collide(self.c, it)

                if hit_p:
                    if it.kind == "BP": p_gain += 1
                    elif it.kind == "HZ": stunned_p = True
                    self.items.remove(it)
                    continue  # removed; don't also check CPU

                if hit_c:
                    if it.kind == "BC": c_gain += 1
                    elif it.kind == "HZ": stunned_c = True
                    self.items.remove(it)

            if p_gain: self.p_score += p_gain
            if c_gain: self.c_score += c_gain
            if stunned_p: self.p.stunned_until = self.t + STUN_TIME
            if stunned_c: self.c.stunned_until = self.t + STUN_TIME

            # Check winner (first to TARGET_SCORE)
            if self.p_score >= TARGET_SCORE and self.c_score >= TARGET_SCORE:
                winner = "tie"
            elif self.p_score >= TARGET_SCORE:
                winner = "player"
            elif self.c_score >= TARGET_SCORE:
                winner = "cpu"

            self._draw()

        # Quick settle screen
        end_txt = "You win!" if winner=="player" else ("CPU wins!" if winner=="cpu" else "Tie!")
        for _ in range(24):
            self._draw()
            draw_text(self.screen, end_txt, (WIN_W//2, WIN_H//2), 48,
                      TEAL if winner=="player" else (RED if winner=="cpu" else TEXT), center=True)
            pg.display.flip()
            clock.tick(FPS)

        return winner

    # ---------- rendering ----------
    def _draw(self):
        self.screen.blit(BG_IMG,(0,0))
        now = pg.time.get_ticks()

        # lane flash cue
        for born, lane in list(self.flash_events):
            age = (now - born)/1000.0
            if age > 0.25:
                self.flash_events.remove((born, lane)); continue
            fxw = int(WIN_W * 0.34)
            fx = pg.transform.smoothscale(FLASH, (fxw, 18))
            fx.set_alpha(int(255*(1.0 - age/0.25)))
            self.screen.blit(fx, fx.get_rect(center=(WIN_W//2, LANES_Y[lane])))

        # items
        for it in self.items:
            spr = BANNER_P if it.kind=="BP" else (BANNER_C if it.kind=="BC" else HAZARD)
            self.screen.blit(spr, spr.get_rect(center=(int(it.x), LANES_Y[it.lane])))

        # runners + small star right on top of head
        def draw_runner(r, spr):
            rr = spr.get_rect(center=(r.x, LANES_Y[r.lane]))
            self.screen.blit(spr, rr)
            if self.t < r.stunned_until:
                star = STARS.copy()
                # quick blink
                star.set_alpha(190 if (now // 120) % 2 == 0 else 120)
                self.screen.blit(star, star.get_rect(midbottom=(rr.centerx, rr.top + 4)))

        draw_runner(self.p, RUN_P)
        draw_runner(self.c, RUN_C)

        # HUD (First to 10)
        draw_text(self.screen, "S K I R M I S H   L A N E S  —  First to 10", (WIN_W//2, 78), 28, TEXT, center=True)
        draw_text(self.screen, f"{self.p_score}", (WIN_W-120, 80), 36, TEAL, center=True)
        draw_text(self.screen, f"{self.c_score}", (120, 80), 36, RED, center=True)

        pg.display.flip()

# Public entry
def run_skirmish_lanes(screen, clock, difficulty="NORMAL"):
    return SkirmishLanes(screen, difficulty=difficulty).run()
