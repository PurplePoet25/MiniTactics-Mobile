import pygame as pg
from config import WIN_W, WIN_H, TITLE
from ui import GameUI

def main():
    pg.init()
    pg.display.set_caption(TITLE)
    # Double buffering + vsync to eliminate grid flashing
    try:
        screen = pg.display.set_mode((WIN_W, WIN_H), pg.DOUBLEBUF, vsync=1)
    except TypeError:
        # Fallback for older Pygame without vsync kw
        screen = pg.display.set_mode((WIN_W, WIN_H), pg.DOUBLEBUF)
    GameUI(screen).run()
    pg.quit()

if __name__ == "__main__":
    main()
