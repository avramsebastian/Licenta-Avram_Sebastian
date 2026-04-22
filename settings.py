class Settings:
    """
    This class contains all the settings for the Jump King - Genetic Algorithm Simulation. 
    It includes parameters for the game window, colors, physics, and AI behavior.
    """

    WIDTH: int = 800
    HEIGHT: int = 600
    FPS: int = 60
    TITLE: str = "Jump King - Genetic Algorithm Simulation"

    BG_COLOR: tuple = (40, 40, 40)      
    PLAYER_COLOR: tuple = (255, 50, 50) 
    PLATFORM_COLOR: tuple = (100, 200, 100) 

    GRAVITY: float = 0.5
    MAX_FALL_SPEED: float = 12.0
    
    MAX_WALK_SPEED: float = 2.5     
    WALK_ACCEL: float = 0.4       
    GROUND_FRICTION: float = 0.75   
    
    MAX_JUMP_CHARGE: int = 30    
    WALK_THRESHOLD: int = 5      
    
    MAX_JUMP_FORCE_Y: float = -15.0  
    MAX_JUMP_FORCE_X: float = 6.0