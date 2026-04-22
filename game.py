import pygame
import sys
from settings import Settings
from player import Player

class Game:
    """
    The main Engine class that handles the Pygame window, event polling, 
    the core game loop, and rendering. It acts as the central controller 
    for all game entities.
    """
    
    screen: pygame.Surface
    clock: pygame.time.Clock
    running: bool
    player: Player

    def __init__(self) -> None:
        """
        Initializes the Pygame display surface, the frame rate clock, 
        the core loop control variables, and spawns the player entity.
        """
        self.screen = pygame.display.set_mode((Settings.WIDTH, Settings.HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.player = Player(Settings.WIDTH // 2, 100)

    def handle_events(self) -> None:
        """
        Processes standard Pygame events like closing the window.
        Input logic has been delegated directly to the Player class for reliability.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

    def update(self) -> None:
        """
        Updates the game state, physics, and AI logic for the current frame.
        Applies velocity to positions and handles basic boundary collisions.
        """
        keys = pygame.key.get_pressed()
        self.player.handle_input(keys)
        
        self.player.update()
        
        self.player.rect.x += int(self.player.vx)
        self.player.rect.y += int(self.player.vy)

        floor_y: int = Settings.HEIGHT - 50
        if self.player.rect.bottom >= floor_y and self.player.vy >= 0:
            self.player.rect.bottom = floor_y
            self.player.vy = 0.0
            self.player.is_grounded = True

        if self.player.rect.left <= 0 or self.player.rect.right >= Settings.WIDTH:
            self.player.wall_bounce()
            
            if self.player.rect.left <= 0:
                self.player.rect.left = 0
            if self.player.rect.right >= Settings.WIDTH:
                self.player.rect.right = Settings.WIDTH

    def draw(self) -> None:
        """
        Clears the screen and renders all game objects, backgrounds, and platforms.
        """
        self.screen.fill(Settings.BG_COLOR)
        
        floor_rect = pygame.Rect(0, Settings.HEIGHT - 50, Settings.WIDTH, 50)
        pygame.draw.rect(self.screen, Settings.PLATFORM_COLOR, floor_rect)
        
        self.player.draw(self.screen)
        
        pygame.display.flip()

    def run(self) -> None:
        """
        The main game loop. Controls the frame rate and the execution order.
        """
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(Settings.FPS)