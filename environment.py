import pygame
import json
from typing import List, Dict, Any, Optional
from settings import Settings

class Platform:
    """
    Represents a physical object in the game world that the player can stand on or collide with.
    Contains physics modifiers like friction or wind to affect the player's movement.
    """

    def __init__(self, x: int, y: int, width: int, height: int, friction: float = 1.0, wind_push: float = 0.0) -> None:
        """
        Initializes the platform with position, size, and physical properties.
        
        params:
            - x: The horizontal starting position of the platform
            - y: The vertical starting position of the platform
            - width: The width of the platform in pixels
            - height: The height of the platform in pixels
            - friction: Modifier for sliding (1.0 is normal, < 1.0 is slippery)
            - wind_push: Horizontal force applied to the player while touching this platform
        """
        self.rect: pygame.Rect = pygame.Rect(x, y, width, height)
        self.friction: float = friction
        self.wind_push: float = wind_push

    def draw(self, surface: pygame.Surface) -> None:
        """
        Renders the platform's collision box on the screen. 
        Currently used for debugging so we can see the invisible platforms over the image.
        
        params:
            - surface: The Pygame display surface where the platform will be drawn
        """
        pygame.draw.rect(surface, Settings.PLATFORM_COLOR, self.rect, 2)
        #pass

class Ramp:
    """
    Represents a diagonal surface in the game, defined by two points (A and B).
    """
    
    def __init__(self, x1: int, y1: int, x2: int, y2: int, friction: float = 1.0, wind_push: float = 0.0) -> None:
        """
        Initializes a new ramp.

        Parameters:
            - x1 (int): The X coordinate of the first point of the ramp.
            - y1 (int): The Y coordinate of the first point of the ramp.
            - x2 (int): The X coordinate of the second point of the ramp.
            - y2 (int): The Y coordinate of the second point of the ramp.
            - friction (float): The friction coefficient (how slippery the ramp is).
            - wind_push (float): The horizontal wind force applied to the player on this ramp.
        """
        if x1 < x2:
            self.x1, self.y1 = x1, y1
            self.x2, self.y2 = x2, y2
        else:
            self.x1, self.y1 = x2, y2
            self.x2, self.y2 = x1, y1
            
        self.friction = friction
        self.wind_push = wind_push

    def get_y_at_x(self, player_x: float) -> Optional[float]:
        """
        Calculates the exact floor height on the ramp at a specific X coordinate.

        Parameters:
            - player_x (float): The current X position of the player's center.

        Returns:
            - float: The exact Y coordinate of the ramp at the given X position.
            - None: If the player is NOT above (between the ends of) the ramp.
        """
        if self.x1 <= player_x <= self.x2:
            return self.y1 + (player_x - self.x1) * (self.y2 - self.y1) / (self.x2 - self.x1)
        return None

    def draw(self, surface: pygame.Surface) -> None:
        """
        Draws a thick line to visually represent the ramp.
        """
        pygame.draw.line(surface, Settings.PLATFORM_COLOR, (self.x1, self.y1), (self.x2, self.y2), 4)
        #pass

class Level:
    """
    Acts as a container for the current scene. 
    Holds the background image and the list of platforms that make up the environment.
    """

    def __init__(self, bg_image_path: str, platforms_data: List[Platform], ramps_data: Optional[List[Ramp]] = None) -> None:
        """
        Initializes the level, loads the background graphic, and stores the platform list.
        
        params:
            - bg_image_path: A string representing the file path to the background image
            - platforms_data: A list of Platform objects that define the physical boundaries
            - ramps_data: A list of Ramp objects that define diagonal surfaces (optional)
        """
        try:
            self.background_image: pygame.Surface = pygame.image.load(bg_image_path).convert()
            self.background_image = pygame.transform.scale(self.background_image, (Settings.WIDTH, Settings.HEIGHT))
        except (FileNotFoundError, pygame.error):
            print(f"WARNING: Could not find background image at '{bg_image_path}'. Using solid color.")
            self.background_image = pygame.Surface((Settings.WIDTH, Settings.HEIGHT))
            self.background_image.fill(Settings.BG_COLOR)
            
        self.platforms: List[Platform] = platforms_data
        self.platform_rects: List[pygame.Rect] = [p.rect for p in self.platforms]
        self.ramps: List[Ramp] = ramps_data if ramps_data is not None else []

    def draw(self, surface: pygame.Surface) -> None:
        """
        Renders the entire level, drawing the background first, then the platform debug outlines.
        
        params:
            - surface: The main Pygame display surface
        """
        surface.blit(self.background_image, (0, 0))
        for platform in self.platforms:
            platform.draw(surface)

        for ramp in self.ramps:
            ramp.draw(surface)


class LevelManager:
    """
    Handles the loading and transitioning of levels from a JSON data file.
    """

    def __init__(self, json_path: str) -> None:
        """
        Loads the JSON file containing all level blueprints into memory.
        
        params:
            - json_path: The relative file path to the JSON configuration file
        """
        self.current_level_index: int = 21
        try:
            with open(json_path, 'r') as file:
                self.level_data: Dict[str, Any] = json.load(file)
        except FileNotFoundError:
            print(f"ERROR: The file {json_path} was not found. Creating an empty layout.")
            self.level_data = {"0": {"background": "", "platforms": []}}

    def get_current_level(self) -> Level:
        """
        Parses the JSON dictionary for the current level index and returns 
        a fully built Level object containing the Background Image and Platform objects.
        """
        level_str: str = str(self.current_level_index)
        
        if level_str not in self.level_data:
            print(f"WARNING: Level {level_str} not found. Defaulting to level 0.")
            level_str = "0"
            self.current_level_index = 0

        data: Dict[str, Any] = self.level_data[level_str]
        bg_path: str = data.get("background", "")
        
        platforms: List[Platform] = []
        for p_data in data.get("platforms", []):
            platform = Platform(
                x=p_data["x"],
                y=p_data["y"],
                width=p_data["width"],
                height=p_data["height"],
                friction=p_data.get("friction", 1.0),
                wind_push=p_data.get("wind_push", 0.0)
            )
            platforms.append(platform)

        ramps: List[Ramp] = []
        for r_data in data.get("ramps", []):
            ramp = Ramp(
                x1=r_data["x1"],
                y1=r_data["y1"],
                x2=r_data["x2"],
                y2=r_data["y2"],
                friction=r_data.get("friction", 1.0),
                wind_push=r_data.get("wind_push", 0.0)
            )
            ramps.append(ramp)
            
        return Level(bg_path, platforms, ramps)