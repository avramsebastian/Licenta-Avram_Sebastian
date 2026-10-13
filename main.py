from __future__ import annotations
from pygame import display, init, quit
from sys import exit
from game import Game
from settings import Settings

def main() -> None:
    """
    Initializes Pygame, sets up the window, and starts the main game engine.
    """
    init()
    display.set_caption(Settings.TITLE)
    
    app: Game = Game()
    app.run()

    quit()
    exit()

if __name__ == "__main__":
    main()