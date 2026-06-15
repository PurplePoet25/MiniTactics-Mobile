# utils.py — shared helpers (safe for top-level execution)
import pygame as pg
from typing import Callable, Tuple
from config import WIDTH, HEIGHT, WIN_W, WIN_H, WHITE, ACCENT, TEXT, SLATE

# ------------------------------------------------------------
# Basic drawing & image helpers
# ------------------------------------------------------------

def load_img(path):
    """
    Load an image and return a Surface. If the display isn't initialized yet,
    skip convert()/convert_alpha() to avoid crashing when modules import assets
    before the window is created.
    """
    surf = pg.image.load(path)
    display_ready = pg.get_init() and pg.display.get_surface() is not None
    if not display_ready:
        return surf
    try:
        return surf.convert_alpha()
    except Exception:
        return surf.convert()

def draw_text(surface, text, pos_or_center, size, color, center=False):
    """
    Render text quickly using a default SysFont. If center=True, 'pos_or_center' is treated as center coords.
    """
    font = size if not isinstance(size, int) else pg.font.SysFont(None, int(size))
    txt  = font.render(text, True, color) if isinstance(text, str) else text
    rect = txt.get_rect()
    if center:
        rect.center = (int(pos_or_center[0]), int(pos_or_center[1]))
    else:
        rect.topleft = (int(pos_or_center[0]), int(pos_or_center[1]))
    surface.blit(txt, rect)
    return rect

def blit_center(surface, surf, center):
    """Blit 'surf' centered at the given (x, y)."""
    surface.blit(surf, surf.get_rect(center=(int(center[0]), int(center[1]))))

def rounded_rect(surface, rect, fill, radius=8, stroke_w=0, stroke_color=None):
    """
    Draw a rounded rectangle. 'rect' may be a pygame.Rect or (x,y,w,h) tuple.
    """
    if not isinstance(rect, pg.Rect):
        rect = pg.Rect(rect)
    pg.draw.rect(surface, fill, rect, border_radius=int(radius))
    if stroke_w and stroke_color:
        pg.draw.rect(surface, stroke_color, rect, int(stroke_w), border_radius=int(radius))

# ------------------------------------------------------------
# Sweet little screen-wide helpers: scrim, fades, modal
# ------------------------------------------------------------

def draw_scrim(surface, alpha=160):
    """Dim the scene with a translucent scrim."""
    scrim = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
    scrim.fill((0, 0, 0, int(alpha)))
    surface.blit(scrim, (0, 0))

def fade(surface, duration_ms=140, mode="out", color=(0, 0, 0)):
    """
    Full-screen fade. mode: "out" -> to black; "in" -> from black.
    Blocks briefly for duration_ms to keep transitions crisp.
    """
    clock = pg.time.Clock()
    overlay = pg.Surface((WIDTH, HEIGHT))
    overlay.fill(color)
    steps = max(1, int(duration_ms / 16))
    for i in range(steps + 1):
        alpha = int(255 * (i / steps)) if mode == "out" else int(255 * (1 - i / steps))
        overlay.set_alpha(alpha)
        surface.blit(overlay, (0, 0))
        pg.display.flip()
        clock.tick(60)

def fade_out_in(surface, half_ms=140, color=(0, 0, 0)):
    fade(surface, half_ms, "out", color)
    fade(surface, half_ms, "in", color)

def choice_modal(surface, title, lines, buttons=("Accept", "Forfeit"), keymap=None):
    """
    Modal dialog that *freezes* the game behind it. Returns the chosen label.
    lines: list[str]
    buttons: tuple/list of labels
    keymap: optional {pygame.K_*: index} mapping
    """
    # Fonts
    font_title = pg.font.SysFont(None, 42)
    font_text  = pg.font.SysFont(None, 28)
    font_btn   = pg.font.SysFont(None, 28)

    # Panel
    panel = pg.Rect(WIDTH // 2 - 360, HEIGHT // 2 - 150, 720, 300)
    selected = 0

    while True:
        # Frozen frame with scrim + panel
        draw_scrim(surface, 170)
        pg.draw.rect(surface, (32, 36, 48), panel, border_radius=14)
        pg.draw.rect(surface, ACCENT, panel, 2, border_radius=14)

        draw_text(surface, title, (panel.x + 24, panel.y + 16), font_title, WHITE)
        yy = panel.y + 70
        for ln in lines:
            draw_text(surface, ln, (panel.x + 24, yy), font_text, WHITE)
            yy += 30

        # Buttons
        btn_w, btn_h, gap = 160, 44, 18
        total_w = len(buttons) * btn_w + (len(buttons) - 1) * gap
        bx = panel.centerx - total_w // 2
        by = panel.bottom - 70
        btn_rects = []
        for i, label in enumerate(buttons):
            br = pg.Rect(bx + i * (btn_w + gap), by, btn_w, btn_h)
            btn_rects.append(br)
            pg.draw.rect(surface, (52, 56, 70), br, border_radius=12)
            pg.draw.rect(surface, ACCENT if i == selected else (90, 98, 120), br, 2, border_radius=12)
            txt = font_btn.render(label, True, WHITE)
            surface.blit(txt, txt.get_rect(center=br.center))

        pg.display.flip()

        # Events (no game updates processed here)
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit(); raise SystemExit
            if e.type == pg.KEYDOWN:
                if e.key in (pg.K_LEFT, pg.K_a):
                    selected = (selected - 1) % len(buttons)
                elif e.key in (pg.K_RIGHT, pg.K_d):
                    selected = (selected + 1) % len(buttons)
                elif e.key in (pg.K_RETURN, pg.K_SPACE):
                    return buttons[selected]
                elif keymap and e.key in keymap:
                    return buttons[keymap[e.key]]
                elif e.key == pg.K_ESCAPE:
                    return buttons[-1]
            if e.type == pg.MOUSEMOTION:
                for i, br in enumerate(btn_rects):
                    if br.collidepoint(e.pos):
                        selected = i
            if e.type == pg.MOUSEBUTTONDOWN and e.button == 1:
                for i, br in enumerate(btn_rects):
                    if br.collidepoint(e.pos):
                        return buttons[i]

# --- math helpers -------------------------------------------------
def clamp(x, lo, hi):
    """Clamp x to the inclusive range [lo, hi]."""
    return lo if x < lo else hi if x > hi else x

def lerp(a, b, t):
    """Linear interpolate between a and b by t in [0..1]."""
    return a + (b - a) * clamp(t, 0.0, 1.0)

def sign(x):
    """Return -1, 0, or +1 depending on x."""
    return (x > 0) - (x < 0)

# ------------------------------------------------------------
# Accept/Forfeit modal + minigame-in-panel helpers (flicker-free)
# ------------------------------------------------------------

def _centered_rect(w: int, h: int) -> pg.Rect:
    return pg.Rect((WIN_W - w) // 2, (WIN_H - h) // 2, w, h)

def accept_forfeit_modal(screen: pg.Surface, clock: pg.time.Clock, title: str, body: str) -> bool:
    """
    Returns True if accepted; False if forfeited/closed.
    """
    panel = _centered_rect(700, 400)
    btn_w, btn_h = 200, 46
    ok_rect = pg.Rect(panel.centerx - btn_w - 12, panel.bottom - btn_h - 22, btn_w, btn_h)
    no_rect = pg.Rect(panel.centerx + 12,          panel.bottom - btn_h - 22, btn_w, btn_h)

    # Fonts
    try:
        font_t = pg.font.SysFont("Segoe UI", 28)
        font_b = pg.font.SysFont("Segoe UI", 22)
    except Exception:
        font_t = pg.font.SysFont("Arial", 28)
        font_b = pg.font.SysFont("Arial", 22)

    while True:
        _ = clock.tick(60)
        for e in pg.event.get():
            if e.type == pg.QUIT:
                return False
            if e.type == pg.MOUSEBUTTONDOWN and e.button == 1:
                if ok_rect.collidepoint(e.pos): return True
                if no_rect.collidepoint(e.pos): return False
            if e.type == pg.KEYDOWN:
                if e.key in (pg.K_RETURN, pg.K_SPACE): return True
                if e.key in (pg.K_ESCAPE, pg.K_n):     return False

        # draw (compose on current frame)
        draw_scrim(screen, 180)
        pg.draw.rect(screen, SLATE, panel, border_radius=16)
        pg.draw.rect(screen, (90, 100, 120), panel, width=2, border_radius=16)

        screen.blit(font_t.render(title, True, WHITE), (panel.x + 24, panel.y + 22))
        for i, line in enumerate(body.split("\n")):
            screen.blit(font_b.render(line, True, WHITE), (panel.x + 24, panel.y + 74 + i * 26))

        # buttons
        def _btn(rect: pg.Rect, label: str, fill=(36, 160, 200)):
            pg.draw.rect(screen, fill, rect, border_radius=10)
            pg.draw.rect(screen, (18, 60, 80), rect, width=2, border_radius=10)
            label_surf = font_b.render(label, True, WHITE)
            screen.blit(label_surf, label_surf.get_rect(center=rect.center))

        _btn(ok_rect, "Accept")
        _btn(no_rect, "Forfeit", fill=(180, 80, 80))

        pg.display.flip()

def run_minigame_in_panel(
    screen: pg.Surface,
    clock: pg.time.Clock,
    minigame_runner: Callable[[pg.Surface, pg.time.Clock], str],
    panel_size: Tuple[int, int] = (920, 560),
    title: str = ""
) -> str:
    """
    Runs a minigame inside a centered modal panel by drawing into an offscreen buffer
    and compositing each flip into the panel (so the game never takes over the window).
    Returns: 'player' | 'cpu' | 'tie'
    """
    # Buffer the minigame will draw into
    buffer = pg.Surface((WIN_W, WIN_H)).convert_alpha()
    buffer.fill((0, 0, 0, 0))  # transparent so we never smear black

    # Capture frozen background so the scene doesn't go black behind the panel
    frozen = screen.copy()

    panel = _centered_rect(*panel_size)
    inner = panel.inflate(-24, -24)

    # Monkey-patch pg.display.flip so the minigame's calls composite into the panel
    real_flip = pg.display.flip

    def _flip_patch():
        # Compose modal on top of frozen frame each flip
        screen.blit(frozen, (0, 0))
        draw_scrim(screen, 180)
        pg.draw.rect(screen, SLATE, panel, border_radius=16)
        pg.draw.rect(screen, (90, 100, 120), panel, width=2, border_radius=16)

        # scale buffer into inner
        scaled = pg.transform.smoothscale(buffer, (inner.w, inner.h))
        screen.blit(scaled, inner.topleft)

        # optional title
        if title:
            try:
                font = pg.font.SysFont("Segoe UI", 20)
            except Exception:
                font = pg.font.SysFont("Arial", 20)
            screen.blit(font.render(title, True, WHITE), (panel.x + 18, panel.y + 14))

        real_flip()

    try:
        pg.display.flip = _flip_patch  # patch
        # Call the minigame with the buffer as its “screen”
        result = minigame_runner(buffer, clock)
    finally:
        pg.display.flip = real_flip  # always restore
        # After minigame, restore the frozen frame once (no black flash)
        screen.blit(frozen, (0, 0))
        real_flip()
    return result
