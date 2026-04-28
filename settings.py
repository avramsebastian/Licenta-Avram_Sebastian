class Settings:
    """
    This class contains all the settings for the Jump King - Genetic Algorithm Simulation. 
    It includes parameters for the game window, colors, physics, file paths, and AI behavior.
    """

    # Window Settings
    WIDTH: int = 1200
    HEIGHT: int = 900
    FPS: int = 60
    TITLE: str = "Jump King - Genetic Algorithm Simulation"

    # File Paths
    LEVEL_DATA_PATH: str = "levels.json"

    # Colors
    BG_COLOR: tuple[int,int,int] = (40, 40, 40)      
    PLAYER_COLOR: tuple[int,int,int] = (255, 50, 50) 
    PLATFORM_COLOR: tuple[int,int,int] = (100, 200, 100) 

    # Physics Constants
    GRAVITY: float = 0.6
    MAX_FALL_SPEED: float = 20.0
    
    # Movement Constants
    MAX_WALK_SPEED: float = 2.5     
    WALK_ACCEL: float = 0.4         
    GROUND_FRICTION: float = 0.75   
    WALK_THRESHOLD: int = 5      
    
    # Jump Mechanics
    MAX_JUMP_CHARGE: int = 30    
    MIN_JUMP_SPEED: float = 6.0
    MAX_JUMP_SPEED: float = 23.0
    MIN_JUMP_SPEED_X: float = 3.5
    MAX_JUMP_SPEED_X: float = 14.5
    JUMP_CHARGE_CURVE: float = 1.0

    # Wall Bouncing
    WALL_BOUNCE_DAMPING: float = 0.6
    MIN_WALL_BOUNCE_SPEED: float = 0.25

    # Ramp Mechanics
    RAMP_SLIDE_ACCEL: float = 0.25
    RAMP_GRAVITY_FACTOR: float = 0.5
    RAMP_MAX_SPEED: float = 7.0
    RAMP_IDLE_FRICTION: float = 0.998
    RAMP_EDGE_RELEASE: int = 2
    
    # Step/Stair Mechanics
    MAX_STEP_HEIGHT: int = 7