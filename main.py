import pygame
import sys
from game import Game
from settings import Settings

def main() -> None:
    """
    The main entry point for the application. 
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