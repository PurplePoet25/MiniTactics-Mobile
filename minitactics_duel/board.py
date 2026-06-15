# board.py
from enum import Enum
from config import GRID_SIZE

class TileStatus(Enum):
    NORMAL    = 0
    CORRUPTED = 1

class Cell:
    def __init__(self, duel_type: str):
        self.duel_type = duel_type
        self.status = TileStatus.NORMAL
        self.piece = None
        # NOTE: counts down ONLY on corrupt rounds
        self.corrupt_timer = 0   # when set (2), it decrements on each CORRUPT round until 0 -> NORMAL

class BoardState:
    def __init__(self, duel_map):
        self.grid = [[Cell(duel_map[r][c]) for c in range(GRID_SIZE)]
                     for r in range(GRID_SIZE)]

    def get(self, r, c) -> Cell:
        return self.grid[r][c]

    def lines_for(self, owner):
        G = GRID_SIZE
        lines = []
        # rows
        for r in range(G):
            if all(self.grid[r][c].piece and self.grid[r][c].piece.owner == owner for c in range(G)):
                lines.append([(r,c) for c in range(G)])
        # cols
        for c in range(G):
            if all(self.grid[r][c].piece and self.grid[r][c].piece.owner == owner for r in range(G)):
                lines.append([(r,c) for r in range(G)])
        # diags
        diag = [(i,i) for i in range(G)]
        if all(self.grid[r][c].piece and self.grid[r][c].piece.owner == owner for r,c in diag):
            lines.append(diag)
        anti = [(i,G-1-i) for i in range(G)]
        if all(self.grid[r][c].piece and self.grid[r][c].piece.owner == owner for r,c in anti):
            lines.append(anti)
        return lines

    def clear_line(self, coords):
        for r,c in coords:
            cell = self.grid[r][c]
            if cell.piece:
                cell.piece.reset_on_death()
            cell.piece = None

    # Called ONLY after a CORRUPT round resolves
    def tick_corruption_on_corrupt_round_end(self):
        for row in self.grid:
            for cell in row:
                if cell.status == TileStatus.CORRUPTED and cell.corrupt_timer > 0:
                    cell.corrupt_timer -= 1
                    if cell.corrupt_timer == 0:
                        cell.status = TileStatus.NORMAL
