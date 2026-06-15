# director.py
import random
from config import GRID_SIZE
from board import TileStatus

PHASES = ("tranquil", "strike", "corrupt")

class Director:
    """
    Round machine:
      tranquil  : player -> cpu -> (no world event)
      strike    : player -> cpu -> STRIKE
      corrupt   : player -> cpu -> CORRUPT (tiles last 2 corrupt rounds unless warded)
    """
    def __init__(self):
        self.phase_idx = 0  # 0 tranquil, 1 strike, 2 corrupt

    def phase(self) -> str:
        return PHASES[self.phase_idx]

    def advance(self):
        self.phase_idx = (self.phase_idx + 1) % len(PHASES)

    # ---- Events (called AFTER both sides act) ----
    def do_strike(self, board):
        """Return (r,c, returned_piece or None) or None if nothing was struck."""
        occupied = [(r,c) for r in range(GRID_SIZE) for c in range(GRID_SIZE)
                    if board.get(r,c).piece is not None]
        if not occupied:
            return None
        r,c = random.choice(occupied)
        cell = board.get(r,c)
        if cell.piece.shielded:
            # Pop shield, leave piece
            cell.piece.shielded = False
            cell.piece.shield_expires_phase = None
            return (r,c, None)
        # Knock out
        owner, ptype = cell.piece.owner, cell.piece.ptype
        cell.piece.reset_on_death()
        cell.piece = None
        return (r,c, (owner,ptype))

    def do_corrupt(self, board, ward_tiles: set[tuple[int,int]]):
        """
        Pick one empty NORMAL tile that is not in ward_tiles and mark it CORRUPTED
        for two corrupt rounds. Returns (r,c) or None.
        """
        empties = [(r,c) for r in range(GRID_SIZE) for c in range(GRID_SIZE)
                   if board.get(r,c).piece is None
                   and board.get(r,c).status == TileStatus.NORMAL
                   and (r,c) not in ward_tiles]
        if not empties:
            return None
        r,c = random.choice(empties)
        cell = board.get(r,c)
        cell.status = TileStatus.CORRUPTED
        cell.corrupt_timer = 2   # lasts across 2 future CORRUPT phases
        return (r,c)
