import pygame
import sys
from game import Game
from settings import Settings

def main() -> None:
    """
    Initializes Pygame, sets up the window, and starts the main game engine.
    """
    pygame.init()
    pygame.display.set_caption(Settings.TITLE)
    
    app: Game = Game()
    app.run()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()