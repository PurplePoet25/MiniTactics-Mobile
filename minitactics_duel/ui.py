# ui.py — MiniTactics: Pocket Warboard Mobile
# A mobile-first experience layer built on the original Duel Edition rules/assets.

import random
import time
import pygame as pg

from config import *
from utils import load_img, draw_text, blit_center, rounded_rect, run_minigame_in_panel, accept_forfeit_modal
from pieces import Owner, PieceType, PieceState, sheet_crop_for
from board import BoardState, TileStatus
from director import Director

from duels.rune_weave import run_rune_weave
from duels.guard_break import run_guard_break
from duels.skirmish_lanes import run_skirmish_lanes
from duels.arc_shot import run_arc_shot
from duels.sudden_spark import run_sudden_spark

_PTYPE_NAME = {PieceType.MAGE: "Mage", PieceType.SHIELDER: "Shielder", PieceType.SOLDIER: "Soldier"}
_COLS = "ABC"
def cell_label(r, c): return f"{_COLS[c]}{r+1}"

class Inventory:
    def __init__(self, owner: Owner):
        self.owner = owner
        self.slots = [PieceType.MAGE, PieceType.SHIELDER, PieceType.SOLDIER]
    def available_types(self): return [t for t in self.slots if t is not None]
    def take_by_index(self, idx):
        if 0 <= idx < len(self.slots) and self.slots[idx] is not None:
            t = self.slots[idx]; self.slots[idx] = None; return t
        return None
    def put_back_index(self, idx, t):
        if 0 <= idx < len(self.slots) and self.slots[idx] is None: self.slots[idx] = t
    def add(self, t):
        for i, s in enumerate(self.slots):
            if s is None:
                self.slots[i] = t; return True
        return False
    def take_type(self, t):
        for i, s in enumerate(self.slots):
            if s == t:
                self.slots[i] = None; return True
        return False

class GameUI:
    def __init__(self, screen: pg.Surface):
        self.screen = screen
        self.clock = pg.time.Clock()

        # Assets from the supplied project. No extra image files required.
        self.board_img = pg.transform.smoothscale(load_img(asset("tiles", "grid.png")), (BOARD_PX, BOARD_PX))
        self.sel_img = pg.transform.smoothscale(load_img(asset("tiles", "selected_tile.png")), (CELL_INNER, CELL_INNER))
        self.corr_img = pg.transform.smoothscale(load_img(asset("tiles", "corrupted_tile.png")), (CELL_INNER, CELL_INNER))
        self.corr_fx = pg.transform.smoothscale(load_img(asset("effects", "corrupt_sizzle.png")), (CELL_INNER, CELL_INNER))
        self.burst_fx = pg.transform.smoothscale(load_img(asset("effects", "line_clear_burst.png")), (CELL_INNER, CELL_INNER))
        self.strike_fx = pg.transform.smoothscale(load_img(asset("effects", "strike_marker.png")), (CELL_INNER, CELL_INNER))
        self.sheet = load_img(asset("pieces", "pieces.png"))
        self.ring_s = pg.transform.smoothscale(load_img(asset("pieces", "shield_ring.png")), (RING_PX, RING_PX))
        self.skull_s = pg.transform.smoothscale(load_img(asset("pieces", "minion_token_skull.png")), (CLAIM_SKULL_PX, CLAIM_SKULL_PX))

        # Portrait layout: board first, controls below. Thumb-safe.
        self.header_rect = pg.Rect(18, 14, WIN_W - 36, 108)
        self.board_rect = pg.Rect((WIN_W - BOARD_PX)//2, self.header_rect.bottom + 16, BOARD_PX, BOARD_PX)
        self.log_rect = pg.Rect(18, self.board_rect.bottom + 14, WIN_W - 36, 118)
        self.controls_rect = pg.Rect(18, self.log_rect.bottom + 14, WIN_W - 36, WIN_H - self.log_rect.bottom - 32)

        rnd = random.Random()
        duel_types = ["rune_weave", "guard_break", "skirmish_lanes", "arc_shot", "sudden_spark"]
        self.board = BoardState([[rnd.choice(duel_types) for _ in range(GRID_SIZE)] for __ in range(GRID_SIZE)])
        self._mg_pool = duel_types[:]
        self._mg_cycle = []

        self.player_hp = START_HP
        self.cpu_hp = START_HP
        self.inv_p = Inventory(Owner.PLAYER)
        self.inv_c = Inventory(Owner.CPU)
        self.phase_count = 1
        self.director = Director()
        self.ward_next_corrupt = set()
        self.cpu_ward_next_corrupt = set()

        self.info_title = "Your turn"
        self.info = "Tap a piece in your hand, then tap a glowing tile. Tap board pieces to move or use Power."
        self.event_feed = ["Welcome to Pocket Warboard.", "Make three-in-a-row to damage the enemy."]
        self.selected = None
        self.targeting = None
        self.held_piece = None  # {ptype, slot_idx}
        self.dragging = None
        self.input_lock = None
        self.cpu_thinking = False
        self.cpu_pending_attack = None
        self.cpu_pending_desc = None

        self.flash_strike = None
        self.flash_claim = None
        self.flash_bursts = []
        self.animated_piece = None  # {owner, ptype, start, end, t0, dur, remove_src, place_dst}
        self.power_button = pg.Rect(0, 0, 0, 0)
        self.cancel_button = pg.Rect(0, 0, 0, 0)

        self._nudge_px = 5
        self._nudges = {(0,0):(5,5),(0,1):(0,5),(0,2):(-5,5),(1,0):(5,0),(1,1):(0,0),(1,2):(-5,0),(2,0):(5,-5),(2,1):(0,-5),(2,2):(-5,-5)}

    # ---------- Messaging / blocking animation ----------
    def log(self, msg):
        self.event_feed.append(msg)
        self.event_feed = self.event_feed[-4:]
        self.info = msg

    def banner(self, title, body="", ms=900):
        self.info_title = title
        if body: self.log(body)
        t0 = pg.time.get_ticks()
        while pg.time.get_ticks() - t0 < ms:
            for e in pg.event.get([pg.QUIT]):
                if e.type == pg.QUIT: pg.quit(); raise SystemExit
            self.draw(pg.mouse.get_pos(), overlay=(title, body))
            self.clock.tick(FPS)

    def _block_ms(self, ms):
        t0 = pg.time.get_ticks()
        while pg.time.get_ticks() - t0 < ms:
            for e in pg.event.get([pg.QUIT]):
                if e.type == pg.QUIT: pg.quit(); raise SystemExit
            self.draw(pg.mouse.get_pos())
            self.clock.tick(FPS)

    def animate_piece_move(self, sr, sc, dr, dc, owner, ptype, ms=None, message=None, mutate=True):
        if message:
            self.log(message)
        if ms is None: ms = ANIM["piece_move"]
        src_cell = self.board.get(sr, sc)
        dst_cell = self.board.get(dr, dc)
        moving_piece = src_cell.piece if src_cell.piece else PieceState(owner, ptype)
        if mutate and src_cell.piece:
            src_cell.piece = None
        self.animated_piece = {
            "owner": owner, "ptype": ptype, "start": self.center(sr, sc), "end": self.center(dr, dc),
            "t0": pg.time.get_ticks(), "dur": max(1, ms), "piece": moving_piece,
        }
        while True:
            elapsed = pg.time.get_ticks() - self.animated_piece["t0"]
            if elapsed >= ms: break
            for e in pg.event.get([pg.QUIT]):
                if e.type == pg.QUIT: pg.quit(); raise SystemExit
            self.draw(pg.mouse.get_pos())
            self.clock.tick(FPS)
        self.animated_piece = None
        if mutate:
            dst_cell.piece = moving_piece
        self.draw(pg.mouse.get_pos())

    def animate_piece_enter(self, dr, dc, owner, ptype, ms=None, message=None, mutate=True):
        """Readable mobile placement animation from the owner hand area into a board cell."""
        if message:
            self.log(message)
        if ms is None:
            ms = ANIM["piece_move"]
        if owner == Owner.PLAYER:
            start = (WIN_W // 2, min(WIN_H - 48, self.controls_rect.y + 58))
        else:
            start = (self.header_rect.right - 82, self.header_rect.y + 74)
        self.animated_piece = {
            "owner": owner, "ptype": ptype, "start": start, "end": self.center(dr, dc),
            "t0": pg.time.get_ticks(), "dur": max(1, ms), "piece": PieceState(owner, ptype),
        }
        while True:
            elapsed = pg.time.get_ticks() - self.animated_piece["t0"]
            if elapsed >= ms:
                break
            for e in pg.event.get([pg.QUIT]):
                if e.type == pg.QUIT:
                    pg.quit(); raise SystemExit
            self.draw(pg.mouse.get_pos())
            self.clock.tick(FPS)
        self.animated_piece = None
        if mutate:
            self.board.get(dr, dc).piece = PieceState(owner, ptype)
        self.draw(pg.mouse.get_pos())

    # ---------- Geometry ----------
    def cell_at(self, pos):
        if not self.board_rect.collidepoint(pos): return None
        c = int((pos[0] - self.board_rect.x) // CELL_PX)
        r = int((pos[1] - self.board_rect.y) // CELL_PX)
        return (r, c) if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE else None
    def cell_rect(self, r, c):
        x = self.board_rect.x + c * CELL_PX + GRID_INSET
        y = self.board_rect.y + r * CELL_PX + GRID_INSET
        dx, dy = self._nudges.get((r, c), (0, 0))
        return pg.Rect(x + dx, y + dy, CELL_INNER, CELL_INNER)
    def center(self, r, c):
        rc = self.cell_rect(r, c); return (rc.centerx, rc.centery)

    # ---------- Drawing ----------
    def draw_piece(self, center, owner, ptype, px):
        sub = sheet_crop_for(ptype, owner, self.sheet)
        sub = pg.transform.smoothscale(sub, (px, px))
        self.screen.blit(sub, sub.get_rect(center=(int(center[0]), int(center[1]))))

    def draw_hearts(self, x, y, n, color=TEXT):
        # Drawn as pips instead of text hearts so Android/Linux missing-glyph fonts never show boxes.
        n = max(0, int(n))
        for i in range(START_HP):
            cx = int(x + i * 30 + 10)
            cy = int(y + 17)
            fill = color if i < n else (48, 52, 66)
            pg.draw.circle(self.screen, fill, (cx, cy), 9)
            pg.draw.circle(self.screen, color, (cx, cy), 9, 2)

    def draw_header(self):
        rounded_rect(self.screen, self.header_rect, CARD_BG, 18, 2, CARD_STROKE)
        draw_text(self.screen, "MiniTactics", (self.header_rect.x + 18, self.header_rect.y + 12), 34, TEXT)
        phase = self.director.phase().title()
        draw_text(self.screen, f"Round {self.phase_count} · {phase}", (self.header_rect.x + 18, self.header_rect.y + 54), 24, ACCENT_DIM)
        draw_text(self.screen, "YOU", (self.header_rect.right - 214, self.header_rect.y + 16), 20, TEAL)
        self.draw_hearts(self.header_rect.right - 168, self.header_rect.y + 10, self.player_hp, TEAL)
        draw_text(self.screen, "CPU", (self.header_rect.right - 214, self.header_rect.y + 56), 20, RED)
        self.draw_hearts(self.header_rect.right - 168, self.header_rect.y + 50, self.cpu_hp, RED)

    def valid_power_targets(self):
        if not self.targeting: return []
        kind, (sr, sc) = self.targeting
        if kind == "mage":
            return [(r,c) for r in range(GRID_SIZE) for c in range(GRID_SIZE) if self.board.get(r,c).piece is None and self.board.get(r,c).status == TileStatus.NORMAL]
        if kind == "shield":
            pts = [(sr,sc),(sr-1,sc),(sr+1,sc),(sr,sc-1),(sr,sc+1)]
            return [(r,c) for r,c in pts if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE and self.board.get(r,c).piece and self.board.get(r,c).piece.owner == Owner.PLAYER]
        pts = [(sr-1,sc-1),(sr-1,sc+1),(sr+1,sc-1),(sr+1,sc+1)]
        return [(r,c) for r,c in pts if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE and self.board.get(r,c).piece and self.board.get(r,c).piece.owner == Owner.CPU]

    def draw_board(self, mouse):
        self.screen.blit(self.board_img, self.board_rect.topleft)

        # Decide legal/interesting highlights before drawing pieces, so highlights sit under pieces.
        highlights = []
        if self.held_piece:
            highlights = [(r,c) for r in range(GRID_SIZE) for c in range(GRID_SIZE)
                          if self.board.get(r,c).piece is None and self.board.get(r,c).status == TileStatus.NORMAL]
        elif self.targeting:
            highlights = self.valid_power_targets()
        elif self.selected:
            sr, sc = self.selected
            highlights = [(sr,sc)]
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                rr, cc = sr + dr, sc + dc
                if 0 <= rr < GRID_SIZE and 0 <= cc < GRID_SIZE:
                    highlights.append((rr,cc))
        else:
            rc = self.cell_at(mouse)
            if rc:
                highlights = [rc]

        # Tile overlays first.
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                cell = self.board.get(r, c)
                if cell.status == TileStatus.CORRUPTED:
                    self.screen.blit(self.corr_img, self.cell_rect(r,c).topleft)
        for rr, cc in highlights:
            self.screen.blit(self.sel_img, self.cell_rect(rr,cc).topleft)

        # Pieces above highlights.
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                cell = self.board.get(r, c)
                if cell.piece:
                    self.draw_piece(self.center(r,c), cell.piece.owner, cell.piece.ptype, PIECE_PX)
                    if getattr(cell.piece, "shielded", False):
                        blit_center(self.screen, self.ring_s, self.center(r,c))

        # Effects above everything.
        now = pg.time.get_ticks()
        if self.flash_strike and now < self.flash_strike[2]:
            r,c,_ = self.flash_strike; self.screen.blit(self.strike_fx, self.cell_rect(r,c).topleft)
        elif self.flash_strike:
            self.flash_strike = None
        if self.flash_claim and now < self.flash_claim[2]:
            r,c,_ = self.flash_claim; blit_center(self.screen, self.skull_s, self.center(r,c))
        elif self.flash_claim:
            self.flash_claim = None
        self.flash_bursts = [(r,c,t) for r,c,t in self.flash_bursts if now < t]
        for r,c,t in self.flash_bursts:
            self.screen.blit(self.burst_fx, self.cell_rect(r,c).topleft)
        if self.animated_piece:
            a = self.animated_piece
            t = min(1.0, (now - a["t0"]) / a["dur"])
            t = t*t*(3-2*t)
            x = a["start"][0] + (a["end"][0] - a["start"][0]) * t
            y = a["start"][1] + (a["end"][1] - a["start"][1]) * t
            self.draw_piece((x,y), a["owner"], a["ptype"], PIECE_PX)

    def draw_log(self):
        rounded_rect(self.screen, self.log_rect, CARD_BG, 18, 2, CARD_STROKE)
        draw_text(self.screen, self.info_title, (self.log_rect.x + 18, self.log_rect.y + 12), 25, TEXT)
        lines = self.event_feed[-3:]
        for i, line in enumerate(lines):
            draw_text(self.screen, "• " + line, (self.log_rect.x + 18, self.log_rect.y + 46 + i*25), 21, TEXT_DIM)

    def draw_controls(self):
        rounded_rect(self.screen, self.controls_rect, CARD_BG, 18, 2, CARD_STROKE)
        draw_text(self.screen, "Your Hand", (self.controls_rect.x + 18, self.controls_rect.y + 14), 28, TEXT)
        slot_y = self.controls_rect.y + 84
        gap = 34
        total = 3 * 132 + 2 * gap
        x0 = self.controls_rect.centerx - total // 2
        self._inv_rects = []
        for i, ptype in enumerate(self.inv_p.slots):
            rect = pg.Rect(x0 + i*(132+gap), slot_y, 132, 132)
            self._inv_rects.append((rect, ptype, i))
            fill = (34, 40, 54) if not (self.held_piece and self.held_piece.get("slot_idx") == i) else (50, 70, 78)
            rounded_rect(self.screen, rect, fill, 18, 2, TEAL if self.held_piece and self.held_piece.get("slot_idx") == i else CARD_STROKE)
            if ptype:
                self.draw_piece(rect.center, Owner.PLAYER, ptype, INV_PIECE_PX)
                draw_text(self.screen, _PTYPE_NAME[ptype], (rect.centerx, rect.bottom + 8), 20, TEXT_DIM, True)
            else:
                draw_text(self.screen, "empty", rect.center, 20, MUTED, True)
        # Action buttons
        by = self.controls_rect.bottom - 78
        self.power_button = pg.Rect(self.controls_rect.x + 22, by, 300, 56)
        self.cancel_button = pg.Rect(self.controls_rect.right - 322, by, 300, 56)
        can_power = bool(self.selected and self.board.get(*self.selected).piece and self.board.get(*self.selected).piece.power_ready)
        rounded_rect(self.screen, self.power_button, (34, 82, 96) if can_power else (42, 44, 54), 16, 2, TEAL if can_power else CARD_STROKE)
        rounded_rect(self.screen, self.cancel_button, (58, 42, 42), 16, 2, RED)
        draw_text(self.screen, "POWER", self.power_button.center, 24, TEXT if can_power else MUTED, True)
        draw_text(self.screen, "CANCEL", self.cancel_button.center, 24, TEXT, True)

    def draw(self, mouse, overlay=None):
        self.screen.fill(SLATE)
        self.draw_header()
        self.draw_board(mouse)
        self.draw_log()
        self.draw_controls()
        if self.dragging and not self.input_lock:
            self.draw_piece(mouse, Owner.PLAYER, self.dragging["ptype"], INV_PIECE_PX)
        if overlay:
            title, body = overlay
            scrim = pg.Surface((WIN_W, WIN_H), pg.SRCALPHA); scrim.fill((0,0,0,120)); self.screen.blit(scrim, (0,0))
            panel = pg.Rect(36, WIN_H//2 - 118, WIN_W - 72, 236)
            rounded_rect(self.screen, panel, (24, 28, 40), 22, 2, ACCENT)
            draw_text(self.screen, title, (panel.centerx, panel.y + 54), 36, TEXT, True)
            if body: draw_text(self.screen, body, (panel.centerx, panel.y + 118), 24, TEXT_DIM, True)
        pg.display.flip()

    # ---------- Rules ----------
    def _next_minigame(self):
        if not self._mg_cycle:
            self._mg_cycle = self._mg_pool[:]
            random.shuffle(self._mg_cycle)
        return self._mg_cycle.pop()

    def _current_difficulty(self):
        if self.cpu_hp >= 3: return "EASY"
        if self.cpu_hp == 2: return "NORMAL"
        return "HARD"

    def run_duel(self, _requested=None):
        difficulty = self._current_difficulty()
        mg = self._next_minigame()
        panel_size = (WIN_W - 36, min(850, WIN_H - 160))
        self.banner("Duel!", f"{mg.replace('_',' ').title()} · {difficulty}", 700)
        runners = {
            "rune_weave": lambda buf, clk: run_rune_weave(buf, clk, difficulty=difficulty),
            "guard_break": lambda buf, clk: run_guard_break(buf, clk, difficulty=difficulty),
            "skirmish_lanes": lambda buf, clk: run_skirmish_lanes(buf, clk, difficulty=difficulty),
            "arc_shot": lambda buf, clk: run_arc_shot(buf, clk, difficulty=difficulty),
            "sudden_spark": lambda buf, clk: run_sudden_spark(buf, clk, difficulty=difficulty),
        }
        try:
            return run_minigame_in_panel(self.screen, self.clock, runners[mg], panel_size, title=f"{mg.replace('_',' ').title()} — {difficulty}")
        except Exception as ex:
            self.log(f"Duel fallback used: {type(ex).__name__}")
            self._block_ms(200)
            return random.choice(["player", "cpu"])

    def modal_challenged(self, attacker_is_cpu, attacker_desc="", defender_desc=""):
        title = "CPU Challenges!" if attacker_is_cpu else "Challenge!"
        body = f"{attacker_desc}\nvs\n{defender_desc}\nAccept the duel or forfeit the tile."
        return accept_forfeit_modal(self.screen, self.clock, title, body)

    def _pure_lines_for(self, owner):
        return self.board.lines_for(owner)

    def can_initiate_vs(self, attacker_ptype, defender_ptype, defender_shielded=False):
        if defender_shielded: return False
        if attacker_ptype == PieceType.MAGE: return True
        if attacker_ptype == PieceType.SOLDIER: return defender_ptype in (PieceType.SOLDIER, PieceType.SHIELDER)
        if attacker_ptype == PieceType.SHIELDER: return defender_ptype == PieceType.SHIELDER
        return False

    def try_place(self, ptype, r, c):
        cell = self.board.get(r,c)
        if cell.status == TileStatus.CORRUPTED:
            self.log("That tile is corrupted. It is blocked for now."); return False
        if cell.piece is not None:
            self.log("That tile is occupied."); return False
        self.animate_piece_enter(r, c, Owner.PLAYER, ptype, ANIM["piece_move"], f"Your {_PTYPE_NAME[ptype]} enters {cell_label(r,c)}.", mutate=True)
        self.banner("Piece Placed", f"Your {_PTYPE_NAME[ptype]} is now on {cell_label(r,c)}.", 420)
        return True

    def try_move(self, src, dst, attacker_is_cpu=False):
        sr,sc = src; dr,dc = dst
        if abs(sr-dr) + abs(sc-dc) != 1:
            if not attacker_is_cpu: self.log("Pieces move one tile orthogonally.")
            return False
        s = self.board.get(sr,sc); d = self.board.get(dr,dc)
        if not s.piece: return False
        if attacker_is_cpu and s.piece.owner != Owner.CPU: return False
        if (not attacker_is_cpu) and s.piece.owner != Owner.PLAYER: return False
        if d.status == TileStatus.CORRUPTED:
            if not attacker_is_cpu: self.log("Corrupted tiles block movement.")
            return False
        if d.piece and s.piece.owner != d.piece.owner:
            if not self.can_initiate_vs(s.piece.ptype, d.piece.ptype, getattr(d.piece, "shielded", False)):
                if not attacker_is_cpu: self.log("That matchup cannot initiate an attack.")
                return False
            self._resolve_duel_with_shield_logic(attacker_is_cpu, sr,sc, dr,dc)
            self.selected = None; self.targeting = None
            return True
        if d.piece is None:
            owner, ptype = s.piece.owner, s.piece.ptype
            msg = ("CPU moves " if attacker_is_cpu else "You move ") + f"{_PTYPE_NAME[ptype]}: {cell_label(sr,sc)} → {cell_label(dr,dc)}."
            self.animate_piece_move(sr,sc,dr,dc,owner,ptype,ANIM["cpu_piece_move"] if attacker_is_cpu else ANIM["piece_move"], msg, mutate=True)
            self.selected = None; self.targeting = None
            return True
        return False

    def _resolve_duel_with_shield_logic(self, attacker_is_cpu, sr, sc, dr, dc):
        s_cell, d_cell = self.board.get(sr,sc), self.board.get(dr,dc)
        if not (s_cell.piece and d_cell.piece): return
        attacker = s_cell.piece
        defender = d_cell.piece
        atk_name = "CPU" if attacker_is_cpu else "You"
        self.banner("Attack!", f"{atk_name} challenges {cell_label(dr,dc)}.", 700)
        winner = self.run_duel(None)
        att_winner = "cpu" if attacker_is_cpu else "player"
        if winner == att_winner:
            if getattr(defender, "shielded", False):
                defender.shielded = False; defender.shield_expires_phase = None
                self.banner("Shield Break", "The shield absorbs the attack.", 750); return
            # Captured defender returns to loser inventory.
            (self.inv_p if attacker_is_cpu else self.inv_c).add(defender.ptype)
            defender.reset_on_death()
            owner, ptype = attacker.owner, attacker.ptype
            d_cell.piece = None
            self.animate_piece_move(sr,sc,dr,dc,owner,ptype,ANIM["claim_skull"], f"{atk_name} wins the duel and claims {cell_label(dr,dc)}.", mutate=True)
            self.flash_claim = (dr, dc, pg.time.get_ticks() + ANIM["claim_skull"])
            self._block_ms(ANIM["claim_skull"])
        else:
            # Attacker fails and returns to defender inventory.
            (self.inv_c if attacker_is_cpu else self.inv_p).add(attacker.ptype)
            self.banner("Attack Failed", f"{atk_name} lost the duel. The attacking piece retreats to hand.", 850)
            attacker.reset_on_death()
            s_cell.piece = None
            self._block_ms(ANIM["settle_small"])

    def start_power(self, r, c):
        p = self.board.get(r,c).piece
        if not (p and p.owner == Owner.PLAYER): return False
        if not p.power_ready:
            self.log("That piece has already used its power."); return False
        if p.ptype == PieceType.MAGE:
            self.targeting = ("mage", (r,c)); self.banner("Mage Power", "Tap an empty tile to ward it from the next Corrupt.", 700)
        elif p.ptype == PieceType.SHIELDER:
            self.targeting = ("shield", (r,c)); self.banner("Shielder Power", "Tap yourself or an adjacent ally to guard them.", 700)
        else:
            self.targeting = ("soldier", (r,c)); self.banner("Soldier Power", "Tap a diagonal enemy to challenge it.", 700)
        return True

    def power_click(self, r, c):
        if not self.targeting: return False
        kind, (sr, sc) = self.targeting
        sp = self.board.get(sr,sc).piece
        if not sp: self.targeting = None; return False
        if kind == "mage":
            cell = self.board.get(r,c)
            if cell.piece is None and cell.status == TileStatus.NORMAL:
                self.ward_next_corrupt.add((r,c)); sp.power_ready = False
                self.targeting = None; self.selected = None
                self.banner("Ward Placed", f"{cell_label(r,c)} will resist the next corruption.", 800); return True
        if kind == "shield":
            cell = self.board.get(r,c)
            if cell.piece and cell.piece.owner == Owner.PLAYER:
                cell.piece.shielded = True; cell.piece.shield_expires_phase = self.phase_count
                sp.power_ready = False; self.targeting = None; self.selected = None
                self.banner("Guard Up", f"{cell_label(r,c)} is protected for this round.", 800); return True
        if kind == "soldier":
            if abs(sr-r) == 1 and abs(sc-c) == 1:
                cell = self.board.get(r,c)
                if cell.piece and cell.piece.owner == Owner.CPU:
                    self._resolve_duel_with_shield_logic(False, sr,sc,r,c)
                    if self.board.get(sr,sc).piece: self.board.get(sr,sc).piece.power_ready = False
                    self.targeting = None; self.selected = None; return True
        self.log("Invalid power target.")
        return False

    # ---------- CPU AI ----------
    def _near_complete_holes(self, owner):
        holes = []
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                cell = self.board.get(r,c)
                if cell.piece is None and cell.status == TileStatus.NORMAL:
                    cell.piece = PieceState(owner, PieceType.MAGE)
                    if self._pure_lines_for(owner): holes.append((r,c))
                    cell.piece = None
        return holes

    def would_complete_line_with(self, owner, t, r, c):
        cell = self.board.get(r,c)
        if cell.piece is not None or cell.status != TileStatus.NORMAL: return False
        cell.piece = PieceState(owner, t)
        ok = bool(self._pure_lines_for(owner))
        cell.piece = None
        return ok

    def _cpu_schedule_attack_if_any(self):
        coords = [(r,c) for r in range(GRID_SIZE) for c in range(GRID_SIZE) if self.board.get(r,c).piece and self.board.get(r,c).piece.owner == Owner.CPU]
        random.shuffle(coords)
        for r,c in coords:
            s = self.board.get(r,c).piece
            for dr,dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                rr,cc = r+dr,c+dc
                if 0 <= rr < GRID_SIZE and 0 <= cc < GRID_SIZE:
                    d = self.board.get(rr,cc)
                    if d.piece and d.piece.owner == Owner.PLAYER and self.can_initiate_vs(s.ptype, d.piece.ptype, getattr(d.piece,"shielded",False)):
                        self.cpu_pending_attack = (r,c,rr,cc)
                        self.cpu_pending_desc = (f"CPU {_PTYPE_NAME[s.ptype]} at {cell_label(r,c)}", f"your {_PTYPE_NAME[d.piece.ptype]} at {cell_label(rr,cc)}")
                        return True
        return False

    def cpu_take_action(self):
        self.banner("Enemy Turn", "Watch the board. The enemy will act now.", 650)
        time.sleep(random.uniform(CPU_THINK_MIN/1000.0, CPU_THINK_MAX/1000.0))
        # 1. Score if possible.
        holes = self._near_complete_holes(Owner.CPU)
        avail = self.inv_c.available_types()
        if holes and avail:
            random.shuffle(holes)
            for r,c in holes:
                for t in avail[:]:
                    if self.inv_c.take_type(t):
                        self.animate_piece_enter(r, c, Owner.CPU, t, ANIM["cpu_piece_move"], f"CPU places {_PTYPE_NAME[t]} at {cell_label(r,c)} to threaten a line.", mutate=True)
                        self.banner("Enemy Places", f"CPU has occupied {cell_label(r,c)}.", 520)
                        return
        # 2. Block player.
        holes = self._near_complete_holes(Owner.PLAYER)
        avail = self.inv_c.available_types()
        if holes and avail:
            holes.sort(key=lambda rc: (rc != (1,1), rc[0], rc[1]))
            r,c = holes[0]
            t = avail[0]
            if self.inv_c.take_type(t):
                self.animate_piece_enter(r, c, Owner.CPU, t, ANIM["cpu_piece_move"], f"CPU blocks your line at {cell_label(r,c)}.", mutate=True)
                self.banner("Enemy Blocks", f"CPU has blocked {cell_label(r,c)}.", 520)
                return
        # 3. Attack if adjacent.
        if self._cpu_schedule_attack_if_any(): return
        # 4. Reposition visibly.
        moves = []
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                s = self.board.get(r,c).piece
                if s and s.owner == Owner.CPU:
                    for dr,dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                        rr,cc = r+dr,c+dc
                        if 0 <= rr < GRID_SIZE and 0 <= cc < GRID_SIZE:
                            d = self.board.get(rr,cc)
                            if d.piece is None and d.status == TileStatus.NORMAL:
                                score = (3 if (rr,cc)==(1,1) else 0) + (1 if rr in (0,2) and cc in (0,2) else 0) + random.random()
                                moves.append((score,(r,c),(rr,cc)))
        if moves:
            moves.sort(reverse=True, key=lambda x: x[0])
            _, src, dst = moves[0]
            s = self.board.get(*src).piece
            self.animate_piece_move(src[0],src[1],dst[0],dst[1],Owner.CPU,s.ptype,ANIM["cpu_piece_move"], f"CPU repositions {_PTYPE_NAME[s.ptype]}: {cell_label(*src)} → {cell_label(*dst)}.", mutate=True)
            return
        # 5. Place anything useful.
        avail = self.inv_c.available_types()
        legal = [(r,c) for r in range(GRID_SIZE) for c in range(GRID_SIZE) if self.board.get(r,c).piece is None and self.board.get(r,c).status == TileStatus.NORMAL]
        if avail and legal:
            legal.sort(key=lambda rc: (rc != (1,1), random.random()))
            r,c = legal[0]; t = avail[0]
            if self.inv_c.take_type(t):
                self.animate_piece_enter(r, c, Owner.CPU, t, ANIM["cpu_piece_move"], f"CPU places {_PTYPE_NAME[t]} at {cell_label(r,c)}.", mutate=True)
                self.banner("Enemy Places", f"CPU has occupied {cell_label(r,c)}.", 520)
                return
        self.banner("Enemy Waits", "CPU has no legal action.", 650)

    def handle_cpu_pending_attack(self):
        if not self.cpu_pending_attack: return
        sr,sc,dr,dc = self.cpu_pending_attack
        atk_desc, dfn_desc = self.cpu_pending_desc or ("", "")
        self.cpu_pending_attack = None; self.cpu_pending_desc = None
        s = self.board.get(sr,sc).piece; d = self.board.get(dr,dc).piece
        if not (s and d and s.owner == Owner.CPU and d.owner == Owner.PLAYER): return
        self.banner("Incoming Attack", f"{atk_desc} targets {dfn_desc}.", 850)
        if getattr(d, "shielded", False):
            self.banner("Shield Holds", "Your shield prevents the attack.", 750); return
        accepted = self.modal_challenged(True, atk_desc, dfn_desc)
        if not accepted:
            self.inv_p.add(d.ptype); d.reset_on_death()
            owner, ptype = s.owner, s.ptype
            self.board.get(dr,dc).piece = None
            self.animate_piece_move(sr,sc,dr,dc,owner,ptype,ANIM["claim_skull"], "You forfeited. CPU claims the tile.", mutate=True)
            return
        self._resolve_duel_with_shield_logic(True, sr,sc,dr,dc)

    # ---------- Events / scoring ----------
    def random_empty_normal_cell(self):
        cells = [(r,c) for r in range(GRID_SIZE) for c in range(GRID_SIZE) if self.board.get(r,c).piece is None and self.board.get(r,c).status == TileStatus.NORMAL]
        return random.choice(cells) if cells else None

    def tornado_relocate_one_other_piece(self, owner, placed_rc):
        dest = self.random_empty_normal_cell()
        owned = [(r,c) for r in range(GRID_SIZE) for c in range(GRID_SIZE) if (r,c) != placed_rc and self.board.get(r,c).piece and self.board.get(r,c).piece.owner == owner]
        if not dest or not owned: return
        sr,sc = random.choice(owned); dr,dc = dest
        p = self.board.get(sr,sc).piece
        self.banner("Tornado!", f"A formed line shakes the board. Watch {_PTYPE_NAME[p.ptype]} move.", 1000)
        self.animate_piece_move(sr,sc,dr,dc,p.owner,p.ptype,ANIM["tornado_move"], f"Tornado shuffled {cell_label(sr,sc)} → {cell_label(dr,dc)}.", mutate=True)

    def tornado_shuffle_after_score(self):
        occupied = [(r,c) for r in range(GRID_SIZE) for c in range(GRID_SIZE) if self.board.get(r,c).piece]
        dests = [(r,c) for r in range(GRID_SIZE) for c in range(GRID_SIZE) if self.board.get(r,c).piece is None and self.board.get(r,c).status == TileStatus.NORMAL]
        if not occupied or not dests:
            return
        sr, sc = random.choice(occupied)
        dr, dc = random.choice(dests)
        p = self.board.get(sr, sc).piece
        self.banner("Tornado!", f"Scoring shakes the warboard. Watch {_PTYPE_NAME[p.ptype]} shuffle.", 900)
        self.animate_piece_move(sr, sc, dr, dc, p.owner, p.ptype, ANIM["tornado_move"], f"Tornado shuffled {cell_label(sr,sc)} → {cell_label(dr,dc)}.", mutate=True)

    def wait_for_strike_if_any(self):
        if self.flash_strike:
            self._block_ms(max(0, self.flash_strike[2] - pg.time.get_ticks()))

    def resolve_phase_end(self):
        phase = self.director.phase()
        if phase == "strike":
            self.banner("Strike Round", "Lightning will hit one occupied tile. Shielded pieces survive.", ANIM["pre_event"])
            strike = self.director.do_strike(self.board)
            if strike:
                r,c,ret = strike
                self.flash_strike = (r,c,pg.time.get_ticks()+ANIM["strike_flash"])
                if ret:
                    owner, ptype = ret
                    self.log(f"Strike hits {cell_label(r,c)}. {_PTYPE_NAME[ptype]} returns to hand.")
                    (self.inv_p if owner == Owner.PLAYER else self.inv_c).add(ptype)
                else:
                    self.log(f"Strike hits {cell_label(r,c)}, but the shield breaks instead.")
                self.wait_for_strike_if_any()
            else:
                self.banner("Strike Fizzles", "No occupied tile was available.", 650)
        elif phase == "corrupt":
            self.banner("Corruption Round", "One empty tile may become blocked. Wards can stop it.", ANIM["pre_event"])
            rc = self.director.do_corrupt(self.board, self.ward_next_corrupt | self.cpu_ward_next_corrupt)
            if rc:
                r,c = rc
                self.log(f"{cell_label(r,c)} becomes corrupted for future corrupt cycles.")
                self._block_ms(ANIM["post_event"])
            else:
                self.banner("Corruption Fails", "No legal tile could be corrupted.", 650)
            self.board.tick_corruption_on_corrupt_round_end()
            self.ward_next_corrupt.clear(); self.cpu_ward_next_corrupt.clear()
        else:
            self.banner("Tranquil Round", "No world event this round. Only line scoring resolves.", 520)

        # Expire shields after the full round is readable.
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                p = self.board.get(r,c).piece
                if p and getattr(p, "shield_expires_phase", None) is not None and p.shield_expires_phase <= self.phase_count:
                    p.shielded = False; p.shield_expires_phase = None

        self.resolve_scoring()
        self.director.advance()
        self.phase_count += 1
        next_phase = self.director.phase().title()
        self.info_title = "Your turn"
        self.log(f"Next round: {next_phase}. Plan around the event.")

    def resolve_scoring(self):
        scored_any = False
        for owner in (Owner.PLAYER, Owner.CPU):
            lines = self._pure_lines_for(owner)
            if not lines:
                continue
            scored_any = True
            label = "You" if owner == Owner.PLAYER else "CPU"
            self.banner(f"{label} Score!", "Three in a row clears and deals 1 damage.", 850)
            if owner == Owner.PLAYER:
                self.cpu_hp -= 1
            else:
                self.player_hp -= 1
            for L in lines:
                for r,c in L:
                    p = self.board.get(r,c).piece
                    if p:
                        (self.inv_p if owner == Owner.PLAYER else self.inv_c).add(p.ptype)
                    self.flash_bursts.append((r,c,pg.time.get_ticks()+ANIM["score_burst"]))
                self.board.clear_line(L)
            self._block_ms(ANIM["score_burst"])
        if scored_any:
            self.tornado_shuffle_after_score()

    def after_player_action(self):
        self.held_piece = None; self.dragging = None; self.selected = None; self.targeting = None
        self.cpu_take_action()
        self.handle_cpu_pending_attack()
        self.resolve_phase_end()

    # ---------- Input ----------
    def handle_tap(self, pos):
        if self.input_lock: return
        if self.cancel_button.collidepoint(pos):
            if self.held_piece: self.inv_p.put_back_index(self.held_piece["slot_idx"], self.held_piece["ptype"])
            self.held_piece = None; self.dragging = None; self.selected = None; self.targeting = None
            self.log("Selection cleared."); return
        if self.power_button.collidepoint(pos):
            if self.selected: self.start_power(*self.selected)
            else: self.log("Select one of your board pieces first.")
            return
        for rect, ptype, idx in getattr(self, "_inv_rects", []):
            if rect.collidepoint(pos) and ptype:
                if self.held_piece: self.inv_p.put_back_index(self.held_piece["slot_idx"], self.held_piece["ptype"])
                taken = self.inv_p.take_by_index(idx)
                if taken:
                    self.held_piece = {"ptype": taken, "slot_idx": idx}
                    self.selected = None; self.targeting = None
                    self.log(f"Selected {_PTYPE_NAME[taken]}. Tap a free tile to place it.")
                return
        rc = self.cell_at(pos)
        if not rc: return
        r,c = rc
        if self.targeting:
            if self.power_click(r,c): self.after_player_action()
            return
        if self.held_piece:
            if self.try_place(self.held_piece["ptype"], r,c): self.after_player_action()
            return
        cell = self.board.get(r,c)
        if self.selected:
            if self.try_move(self.selected, (r,c)): self.after_player_action()
            else:
                if cell.piece and cell.piece.owner == Owner.PLAYER:
                    self.selected = (r,c); self.log(f"Selected {_PTYPE_NAME[cell.piece.ptype]} at {cell_label(r,c)}.")
                else:
                    self.selected = None
            return
        if cell.piece and cell.piece.owner == Owner.PLAYER:
            self.selected = (r,c)
            self.log(f"Selected {_PTYPE_NAME[cell.piece.ptype]} at {cell_label(r,c)}. Tap adjacent tile or POWER.")
        elif cell.piece and cell.piece.owner == Owner.CPU:
            self.log(f"Enemy {_PTYPE_NAME[cell.piece.ptype]} at {cell_label(r,c)}. Move beside it to challenge.")
        else:
            self.log("Select a hand piece or one of your board pieces first.")

    # ---------- Screens ----------
    def splash(self):
        while True:
            for e in pg.event.get():
                if e.type == pg.QUIT: return False
                if e.type in (pg.KEYDOWN, pg.MOUSEBUTTONDOWN, pg.FINGERDOWN): return True
            self.screen.fill(SLATE)
            draw_text(self.screen, "MiniTactics", (WIN_W//2, 250), 54, TEXT, True)
            draw_text(self.screen, "Pocket Warboard", (WIN_W//2, 312), 32, ACCENT_DIM, True)
            draw_text(self.screen, "Tap pieces. Watch every enemy move.", (WIN_W//2, 430), 26, TEXT_DIM, True)
            draw_text(self.screen, "World events are announced before they resolve.", (WIN_W//2, 470), 24, TEXT_DIM, True)
            draw_text(self.screen, "Three in a row damages the enemy.", (WIN_W//2, 510), 24, TEXT_DIM, True)
            draw_text(self.screen, "Tap to begin", (WIN_W//2, 690), 30, TEAL, True)
            pg.display.flip(); self.clock.tick(FPS)

    def run(self):
        if not self.splash(): return
        running = True
        while running:
            for e in pg.event.get():
                if e.type == pg.QUIT: running = False
                elif e.type == pg.FINGERDOWN:
                    self.handle_tap((int(e.x * WIN_W), int(e.y * WIN_H)))
                elif e.type == pg.MOUSEBUTTONDOWN and e.button == 1:
                    self.handle_tap(e.pos)
            self.draw(pg.mouse.get_pos())
            if self.player_hp <= 0 or self.cpu_hp <= 0: break
            self.clock.tick(FPS)
        self.end_screen()

    def end_screen(self):
        msg = "You Win!" if self.player_hp > self.cpu_hp else ("You Lose." if self.player_hp < self.cpu_hp else "Draw.")
        while True:
            for e in pg.event.get():
                if e.type == pg.QUIT: return
                if e.type in (pg.KEYDOWN, pg.MOUSEBUTTONDOWN, pg.FINGERDOWN): return
            self.screen.fill(SLATE)
            draw_text(self.screen, msg, (WIN_W//2, WIN_H//2 - 40), 58, TEXT, True)
            draw_text(self.screen, "Tap to exit", (WIN_W//2, WIN_H//2 + 34), 28, TEXT_DIM, True)
            pg.display.flip(); self.clock.tick(FPS)
