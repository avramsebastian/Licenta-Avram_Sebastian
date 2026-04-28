import pygame
from settings import Settings
from player import Player
from environment import LevelManager, Level

class Game:
    """
    The main Engine class that handles the Pygame window, event polling, 
    the core game loop, collision detection, and level transitions.
    """

    def __init__(self) -> None:
        """
        Initializes the Pygame display, the clock, the level manager, 
        loads the first scene, and spawns the player entity.
        """
        self.screen: pygame.Surface = pygame.display.set_mode((Settings.WIDTH, Settings.HEIGHT))
        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.running: bool = True
        
        self.level_manager: LevelManager = LevelManager(Settings.LEVEL_DATA_PATH)
        self.current_level: Level = self.level_manager.get_current_level()
        
        self.player: Player = Player(Settings.WIDTH // 2, Settings.HEIGHT - 100)

    def handle_events(self) -> None:
        """
        Processes standard Pygame events like closing the window.
        Input logic has been delegated directly to the Player class.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

    def update(self) -> None:
        keys = pygame.key.get_pressed()
        
        self.player.handle_input(keys)
        
        if self.player.is_ghost:
            self.player.update()
        else:
            self.player.update(self.current_level.platform_rects, self.current_level.platforms, getattr(self.current_level, "ramps", []))

        self.check_level_transitions()

    
    def check_level_transitions(self) -> None:
        """
        Checks if the player has jumped past the top of the screen or fallen 
        past the bottom, and transitions the scene accordingly.
        """
        if self.player.rect.bottom < 0:
            self.level_manager.current_level_index += 1
            self.current_level = self.level_manager.get_current_level()
            self.player.rect.bottom = Settings.HEIGHT
            self.player.is_grounded = False

        elif self.player.rect.top > Settings.HEIGHT:
            if self.level_manager.current_level_index > 0:
                self.level_manager.current_level_index -= 1
                self.current_level = self.level_manager.get_current_level()
                self.player.rect.top = 0
                self.player.is_grounded = False
            else:
                self.player.rect.bottom = Settings.HEIGHT
                self.player.vy = 0.0
                self.player.is_grounded = True

        self.player.sync_subpixel_position()

    def draw(self) -> None:
        """
        Clears the screen and renders the current level and the player.
        """
        self.screen.fill(Settings.BG_COLOR)
        
        self.current_level.draw(self.screen)
        
        self.player.draw(self.screen)
        
        pygame.display.flip()

    def run(self) -> None:
        """
        The main game loop. Controls the frame rate and execution order.
        """
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            pygame.display.set_caption(f"Jump King - FPS: {int(self.clock.get_fps())}")
            self.clock.tick(Settings.FPS)