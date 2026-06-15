# duels/arc_shot.py
import os, math, random
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

# ----- assets ---------------------------------------------------------------
BG      = _load_img(["as_bg.png"], alpha=False)
TARGET0 = _load_img(["as_target.png"])
ARROW0  = _load_img(["as_arrow.png"])
PBG     = _load_img(["as_power_bar_bg.png"])
PFILL   = _load_img(["as_power_fill.png"])
DOT_P0  = _load_img(["as_marker_teal.png"])
DOT_C0  = _load_img(["as_marker_red.png"])

BG = pg.transform.smoothscale(BG, (WIN_W, WIN_H))

# target smaller; sprite touches its own border
TGT_SIZE = int(min(WIN_W, WIN_H) * 0.42)
TARGET   = pg.transform.smoothscale(TARGET0, (TGT_SIZE, TGT_SIZE))
TGT_R    = TGT_SIZE // 2

# beads larger for clarity
DOT_SIZE = 32
DOT_P    = pg.transform.smoothscale(DOT_P0, (DOT_SIZE, DOT_SIZE))
DOT_C    = pg.transform.smoothscale(DOT_C0, (DOT_SIZE, DOT_SIZE))

# arrow smaller; keep aspect
ARROW    = pg.transform.smoothscale(
    ARROW0, (int(ARROW0.get_width()*0.10), int(ARROW0.get_height()*0.10))
)

# gravity for a long, smooth arc
G = 1100.0  # px/s^2

# ring scoring (fraction of radius → points)
RING_THRESH = ((0.20, 10), (0.40, 7), (0.65, 5), (1.00, 3))
def ring_score(dist_px, radius):
    r = dist_px / max(1, radius)
    for frac, pts in RING_THRESH:
        if r <= frac: return pts
    return 0

def draw_multiline(surface, text, center_xy, size, color, line_gap=8):
    """Render ASCII-only multiline reliably (split on '\\n')."""
    cx, cy = center_xy
    lines = str(text).split("\n")
    total_h = 0
    # measure
    for i, ln in enumerate(lines):
        total_h += size + (line_gap if i < len(lines)-1 else 0)
    y = cy - total_h//2
    for ln in lines:
        draw_text(surface, ln, (cx, y + size//2), size, color, center=True)
        y += size + line_gap

class ArcShot:
    """
    Best of 3 volleys. Hold LMB to charge, aim with mouse, release to fire.
    Arrow sticks exactly where the last simulated point hits the target plane.
    Markers are stored in target-local coordinates, so they move with the target.
    """
    def __init__(self, screen, difficulty="NORMAL"):
        self.screen = screen

        # CPU aim — make it worse on purpose (more noise, less learning, miss chance)
        if difficulty == "EASY":
            self.cpu_noise, self.cpu_learn = 58, 0.30
            self.cpu_miss_chance = 0.18
            self.move_amp, self.move_hz   = 26, 0.55
        elif difficulty == "HARD":
            self.cpu_noise, self.cpu_learn = 30, 0.55
            self.cpu_miss_chance = 0.06
            self.move_amp, self.move_hz   = 70, 0.95
        else:
            self.cpu_noise, self.cpu_learn = 44, 0.40
            self.cpu_miss_chance = 0.12
            self.move_amp, self.move_hz   = 48, 0.75

        # geometry
        self.anchor = pg.Vector2(int(WIN_W*0.20), int(WIN_H*0.66))
        self.tcx    = int(WIN_W*0.74)
        self.tcy0   = int(WIN_H*0.56)  # base Y; animated around this

        # state
        self.round, self.turn = 1, "player"
        self.p_pts = self.c_pts = 0
        self.p_marks, self.c_marks = [], []  # each = (local_dx, local_dy, pts)
        self.cpu_bias = pg.Vector2()

        # arrow flight
        self.in_flight   = False
        self.pos         = pg.Vector2()
        self.vel         = pg.Vector2()
        self.last_dot    = None  # last trajectory point (for exact bead)
        self.stick_until = 0
        self.stick_pos   = None
        self.stick_rot   = 0.0

        self.time0 = pg.time.get_ticks()/1000.0  # for target motion phase
        self.show_ready_hint = True

    # current target center Y (moving)
    def target_y(self):
        t = pg.time.get_ticks()/1000.0 - self.time0
        return int(self.tcy0 + self.move_amp * math.sin(2*math.pi*self.move_hz*t))

    # ----------- intro / countdown (animated, non-blocking) -----------
    def intro(self):
        """Intro shows background + instructions only (no target/arrow)."""
        clock = pg.time.Clock()
        while True:
            _ = clock.tick(FPS)
            self.screen.blit(BG, (0, 0))
            draw_text(self.screen, "A R C   S H O T", (WIN_W//2, 120), 40, TEXT, center=True)
            # strictly ASCII & explicit newlines
            draw_multiline(
                self.screen,
                "Hold Left Mouse to charge.\n"
                "Aim with the mouse.\n"
                "Release to fire. Arrow sticks if it hits the moving circle.\n"
                "Score by ring. Highest score after 3 shots wins.",
                (WIN_W//2, WIN_H//2 - 6), 24, TEXT, line_gap=10
            )
            draw_text(self.screen, "Click anywhere to start", (WIN_W//2, WIN_H//2 + 100), 22, TEAL, center=True)
            pg.display.flip()
            for e in pg.event.get():
                if e.type == pg.QUIT: return False
                if e.type in (pg.MOUSEBUTTONDOWN, pg.KEYDOWN): return True

    def countdown(self, label_text):
        """Show animated countdown with the target moving (no freezing)."""
        clock = pg.time.Clock()
        for label, dur in [("3",0.52), ("2",0.52), ("1",0.52), ("GO!",0.56)]:
            t0 = pg.time.get_ticks()/1000.0
            while (pg.time.get_ticks()/1000.0 - t0) < dur:
                _ = clock.tick(FPS)
                self._draw_state_static(banner=label_text)
                draw_text(self.screen, label, (WIN_W//2, WIN_H//2),
                          66 if label != "GO!" else 74, TEAL, center=True)
                pg.display.flip()
                for e in pg.event.get():
                    if e.type == pg.QUIT: return False
        pg.event.clear()
        return True

    # ----------- helpers -----------
    def _power_bar(self, p):
        w, h = 360, 22
        base = pg.transform.smoothscale(PBG, (w, h))
        fill = pg.transform.smoothscale(PFILL, (int(clamp(p,0,1)*w), h))
        return base, fill

    def _cpu_aim(self):
        """Pick an angle; solve speed so the mean impact is near (tcx, moving y)."""
        desired = pg.Vector2(self.tcx, self.target_y()) + self.cpu_bias + pg.Vector2(
            random.gauss(0, self.cpu_noise), random.gauss(0, self.cpu_noise)
        )
        # add deliberate miss sometimes
        if random.random() < self.cpu_miss_chance:
            desired.y += random.choice([-1, 1]) * random.uniform(TGT_R*0.6, TGT_R*1.2)

        ty = desired.y
        dx = self.tcx - self.anchor.x
        for _ in range(18):
            a = random.uniform(-math.radians(82), -math.radians(18))
            denom = (ty - self.anchor.y - dx*math.tan(a))
            c2    = math.cos(a)**2
            if denom <= 1e-3: continue
            s_sq  = (G*dx*dx) / (2.0*c2*denom)
            if s_sq <= 0: continue
            s = math.sqrt(s_sq)
            # timing jitter to feel human
            s *= random.uniform(0.96, 1.04)
            return self.anchor.copy(), pg.Vector2(s*math.cos(a), s*math.sin(a))
        # fallback
        a, s = -math.radians(40), 700.0
        return self.anchor.copy(), pg.Vector2(s*math.cos(a), s*math.sin(a))

    def _step_flight(self, dt):
        self.pos.x += self.vel.x * dt
        self.pos.y += self.vel.y * dt
        self.vel.y += G * dt
        self.last_dot = (int(self.pos.x), int(self.pos.y))

    def _stick_and_score(self, shooter="player"):
        """Stick at last_dot if inside the circle; score by ring."""
        hit_x, hit_y = self.last_dot
        cy = self.target_y()
        if abs(hit_y - cy) <= TGT_R:  # inside circle
            dist = abs(hit_y - cy)
            pts  = ring_score(dist, TGT_R)
            local = (0, int(hit_y - cy))  # x=0 in target-local (we always hit at tcx)
            if shooter == "player":
                self.p_pts += pts; self.p_marks.append((local[0], local[1], pts))
            else:
                self.c_pts += pts; self.c_marks.append((local[0], local[1], pts))
            # stick pose using terminal velocity direction (flip sign for visual)
            self.stick_pos   = pg.Vector2(self.tcx, hit_y)
            self.stick_rot   = -math.degrees(math.atan2(self.vel.y, self.vel.x))
            self.stick_until = pg.time.get_ticks() + 650
        self.in_flight = False

    # ----------- main -----------
    def run(self):
        if not self.intro(): return "player"
        if not self.countdown(f"A R C   S H O T — Round {self.round}/3"): return "player"

        clock = pg.time.Clock()
        charging, power = False, 0.0
        power_rate = 0.60  # slower charge

        while self.round <= 3:
            dt = clock.tick(FPS) / 1000.0

            for e in pg.event.get():
                if e.type == pg.QUIT: return "player"
                if self.turn == "player":
                    if e.type == pg.MOUSEBUTTONDOWN and e.button == 1 and not charging and not self.in_flight:
                        charging, power = True, 0.0
                        self.show_ready_hint = False
                    if e.type == pg.MOUSEBUTTONUP and e.button == 1 and charging:
                        charging = False
                        m   = pg.Vector2(pg.mouse.get_pos())
                        ang = clamp(math.atan2((m-self.anchor).y, (m-self.anchor).x),
                                    -math.radians(86), -math.radians(14))
                        speed = 520.0 + 520.0 * clamp(power, 0.08, 1.0)
                        self.pos = self.anchor.copy()
                        self.vel = pg.Vector2(speed*math.cos(ang), speed*math.sin(ang))
                        self.in_flight = True
                        self.last_dot = (int(self.pos.x), int(self.pos.y))

            if charging:
                power = min(1.0, power + power_rate*dt)

            # simulate the live arrow
            if self.in_flight:
                self._step_flight(dt)
                # crossed target plane or fell off-screen: resolve
                if self.pos.x >= self.tcx or self.pos.y > WIN_H + 200:
                    self._stick_and_score("player")
                    self.turn = "cpu"

            # CPU fires after stick delay, with worse accuracy
            if self.turn == "cpu" and not self.in_flight and pg.time.get_ticks() > self.stick_until + 260:
                start, v0 = self._cpu_aim()
                dx = self.tcx - start.x
                t_hit = (dx / v0.x) if v0.x > 1e-3 else 0.8
                hit_y = start.y + v0.y * t_hit + 0.5*G*t_hit*t_hit
                self.last_dot = (int(self.tcx), int(hit_y))
                end_vy = v0.y + G*t_hit
                self.pos, self.vel = pg.Vector2(self.tcx, hit_y), pg.Vector2(v0.x, end_vy)
                self._stick_and_score("cpu")

                # learn a little toward bull (small factor keeps it human)
                cy = self.target_y()
                miss = pg.Vector2(self.tcx, cy) - pg.Vector2(self.tcx, hit_y)
                self.cpu_bias += miss * (self.cpu_learn * 0.15)

                # next round
                self.round += 1
                self.turn = "player"
                self.show_ready_hint = True
                if self.round <= 3:
                    if not self.countdown(f"A R C   S H O T — Round {self.round}/3"): return "player"

            # draw
            self._draw_frame(charging, power)
            pg.display.flip()

        if self.p_pts == self.c_pts: return "tie"
        return "player" if self.p_pts > self.c_pts else "cpu"

    # ----------- drawing -----------
    def _draw_state_static(self, banner=None):
        self.screen.blit(BG, (0, 0))
        cy = self.target_y()
        self.screen.blit(TARGET, TARGET.get_rect(center=(self.tcx, cy)))
        # markers (target-local → world)
        for dx, dy, pts in self.p_marks:
            self.screen.blit(DOT_P, DOT_P.get_rect(center=(self.tcx+dx, cy+dy)))
            draw_text(self.screen, f"+{pts}", (self.tcx+dx, cy+dy-26), 18, TEAL, center=True)
        for dx, dy, pts in self.c_marks:
            self.screen.blit(DOT_C, DOT_C.get_rect(center=(self.tcx+dx, cy+dy)))
            draw_text(self.screen, f"+{pts}", (self.tcx+dx, cy+dy-26), 18, RED, center=True)
        title = banner if banner else f"A R C   S H O T — Round {min(self.round,3)}/3"
        draw_text(self.screen, title, (WIN_W//2, 84), 28, TEXT, center=True)
        draw_text(self.screen, f"YOU {self.p_pts}  |  CPU {self.c_pts}",
                  (WIN_W//2, WIN_H-80), 26, TEXT, center=True)

    def _draw_frame(self, charging, power):
        self._draw_state_static()
        # show a subtle ready hint before first press each round
        if self.show_ready_hint and not charging and not self.in_flight:
            draw_text(self.screen, "Click & hold to shoot", (WIN_W//2, WIN_H-122), 20, TEAL, center=True)

        # charging guideline + power bar; arrow tangent at the anchor
        if charging:
            m   = pg.Vector2(pg.mouse.get_pos())
            ang = clamp(math.atan2((m-self.anchor).y, (m-self.anchor).x),
                        -math.radians(86), -math.radians(14))
            speed = 520.0 + 520.0 * clamp(power, 0.08, 1.0)
            sim_p = self.anchor.copy()
            sim_v = pg.Vector2(speed*math.cos(ang), speed*math.sin(ang))
            step  = 1/120.0
            pts = []
            for _ in range(140):
                if sim_p.x >= self.tcx: break
                pts.append((int(sim_p.x), int(sim_p.y)))
                sim_p.x += sim_v.x * step
                sim_p.y += sim_v.y * step
                sim_v.y += G * step
            for p in pts[::5]:
                pg.draw.circle(self.screen, (235,235,235), p, 2)
            base, fill = self._power_bar(power)
            pb = base.get_rect(midtop=(int(self.anchor.x), int(self.anchor.y) + 34))
            self.screen.blit(base, pb); self.screen.blit(fill, fill.get_rect(topleft=pb.topleft))
            # IMPORTANT: flip rotation sign so the preview arrow looks correct
            arr = pg.transform.rotate(ARROW, -math.degrees(ang))
            self.screen.blit(arr, arr.get_rect(center=(int(self.anchor.x), int(self.anchor.y))))
        # live or stuck arrow
        if self.in_flight:
            rot = -math.degrees(math.atan2(self.vel.y, self.vel.x))  # flipped for correct visual
            arr = pg.transform.rotate(ARROW, rot)
            self.screen.blit(arr, arr.get_rect(center=(int(self.pos.x), int(self.pos.y))))
        elif self.stick_pos is not None and pg.time.get_ticks() <= self.stick_until:
            arr = pg.transform.rotate(ARROW, self.stick_rot)
            self.screen.blit(arr, arr.get_rect(center=(int(self.stick_pos.x), int(self.stick_pos.y))))

# Public entry point
def run_arc_shot(screen, clock, difficulty="NORMAL"):
    return ArcShot(screen, difficulty=difficulty).run()
