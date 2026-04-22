class Settings:
    """
    This class contains all the settings for the Jump King - Genetic Algorithm Simulation. 
    It includes parameters for the game window, colors, physics, and AI behavior.
    Adjusting these settings will affect how the genetic algorithm performs and how the game environment behaves. 
    """

    WIDTH: int = 800
    HEIGHT: int = 600
    FPS: int = 60
    TITLE: str = "Jump King - Genetic Algorithm Simulation"

    BG_COLOR: tuple = (40, 40, 40)      
    PLAYER_COLOR: tuple = (255, 50, 50) 
    PLATFORM_COLOR: tuple = (100, 200, 100) 

    GRAVITY: float = 0.5
    MAX_FALL_SPEED: int = 12
    WALK_SPEED: int = 3
    
    MAX_JUMP_CHARGE: int = 30    
    WALK_THRESHOLD: int = 5      
    
    MAX_JUMP_FORCE_Y: int = -15  
    MAX_JUMP_FORCE_X: int = 6   