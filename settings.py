class Settings:
    """
    This class contains all the settings for the Jump King - Genetic Algorithm Simulation. 
    It includes parameters for the game window, colors, physics, file paths, and AI behavior.
    """

    # Window Settings
    WIDTH: int = 1200
    HEIGHT: int = 900
    FPS: int = 120
    TITLE: str = "Jump King - Genetic Algorithm Simulation"

    # File Paths
    LEVEL_DATA_PATH: str = "levels.json"

    # Physics Constants
    GRAVITY: float = 0.6
    TERMINAL_VELOCITY: float = 20.0
    
    # Player & Image Dimensions
    PLAYER_WIDTH: int = 50
    PLAYER_HEIGHT: int = 65
    IMAGE_SCALEX: int = (int(PLAYER_WIDTH * 1.5))
    IMAGE_SCALEY: int = (int(PLAYER_HEIGHT * 1.5))

    # Player Spawn
    START_X: int = WIDTH // 2
    START_Y: int = 818 - PLAYER_HEIGHT
    START_LEVEL_INDEX: int = 0
    MAX_LEVEL_INDEX: int = 43

    # Movement Constants
    RUN_SPEED: float = 4.0
    ICE_FRICTION: float = 0.2
    ICE_ACCELERATION: float = 0.2
    GHOST_SPEED: int = 15 # this is for testing 
    MAX_FALL_DISTANCE: float = HEIGHT * 0.6
    FALLEN_STUN_TIME: int = 45
    
    # Jump Mechanics
    MIN_JUMP_SPEED: float = 5.0
    MAX_JUMP_SPEED: float = 22.0
    MAX_JUMP_TIMER: int = 30
    JUMP_SPEED_HORIZONTAL: float = 8.0

    # Blizzard Settings
    MAX_BLIZZARD_FORCE: float = 0.3
    BLIZZARD_HOLD_TIME: int = 150
    BLIZZARD_ACCELERATION: float = 0.003
    BLIZZARD_IMG_MULTIPLIER: int = 50

    # Collision Constants
    COLLISION_SNAP_OFFSET: float = 0.1
    MAX_COLLISION_CHECKS: int = 100
    HYBRID_LOOP_LIMIT: int = 4
    SUBSTEP_MARGIN: int = 40
    RAMP_TIP_PUSH_SPEED: float = 4.0
    RAMP_TIP_IGNORE_FRICTION_FRAMES: int = 10

    # Genetic Algorithm Configuration Parameters
    MAX_GENE_STRENGTH: float = 30.0
    GA_POPULATION_SIZE: int = 500
    GA_GENOME_LENGTH: int = 60
    GA_CROSSOVER_RATE: float = 0.85
    GA_MUTATION_RATE_DIRECTION: float = 0.03
    GA_MUTATION_RATE_TYPE: float = 0.04
    GA_MUTATION_RATE_STRENGTH: float = 0.07
    GA_INITIAL_SIGMA: float = 0.25
    GA_ELITISM_COUNT: int = 4
    GA_TOURNAMENT_SIZE: int = 6
    GA_STAGNATION_THRESHOLD: int = 6
    GA_ALLOW_PROGRESSIVE_GROWTH: bool = False  # False for Phase 1 (Static Genome Length), True for Phase 2 (Progressive Genome Growth)
    GA_PROGRESSIVE_GROWTH_AMOUNT: int = 10
    GA_ACTIVE_SCENARIO: str = "REWARDS"  # Options: "REWARDS", "SPEEDRUNNER"
    
    # Coin Settings
    COIN_RADIUS: float = 14.0
    GA_COIN_REWARD_VALUE: float = 500.0
    GA_COIN_PENALTY_VALUE: float = -300.0
    GA_DISTANCE_REWARD_MULTIPLIER: float = 1.0 # default to 1 to not influence the coins values
    GA_TIME_PENALTY_VALUE: float = 0.5 # for the second phase for 1st scenario, need to adjust

    # Colors
    BG_COLOR: tuple[int,int,int] = (40, 40, 40)      
    PLAYER_COLOR: tuple[int,int,int] = (255, 50, 50) 
    PLATFORM_COLOR: tuple[int,int,int] = (190, 60, 255)
    COIN_COLOR: tuple[int,int,int] = (255, 215, 0)
    NEGATIVE_COIN_COLOR: tuple[int,int,int] = (220, 35, 35)