# pieces.py
from enum import Enum

class Owner(Enum):
    PLAYER = 1
    CPU    = 2

class PieceType(Enum):
    MAGE     = "Mage"
    SHIELDER = "Shielder"
    SOLDIER  = "Soldier"

class PieceState:
    def __init__(self, owner, ptype):
        self.owner = owner
        self.ptype = ptype
        self.power_ready = True
        self.shield_expires_turn = None  # one-round shield expiry turn
        self.shielded = False

    def reset_on_death(self):
        self.power_ready = True
        self.shielded = False
        self.shield_expires_turn = None

def sheet_crop_for(ptype, owner, sheet_surf):
    """
    pieces.png layout = 2×3:
      col 0: PLAYER (blue) | col 1: CPU (red)
      rows: 0 Mage, 1 Shielder, 2 Soldier
    """
    import pygame as pg
    row = {PieceType.MAGE:0, PieceType.SHIELDER:1, PieceType.SOLDIER:2}[ptype]
    col = 0 if owner == Owner.PLAYER else 1
    w, h = sheet_surf.get_width(), sheet_surf.get_height()
    cw, ch = w // 2, h // 3
    return sheet_surf.subsurface(pg.Rect(col*cw, row*ch, cw, ch)).copy()
