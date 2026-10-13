from __future__ import annotations
class Settings:
    """
    This class contains all the settings for the GA.
    """

    __slots__ = ()

    # Window settings
    WIDTH: int = 1200
    HEIGHT: int = 900
    FPS: int = 120
    TITLE: str = "Jump King - Genetic Algorithm Simulation"

    # Levels file paths
    LEVEL_DATA_PATH: str = "levels.json"

    # Physics constants
    GRAVITY: float = 0.6
    TERMINAL_VELOCITY: float = 20.0
    
    # Player & image dimensions
    PLAYER_WIDTH: int = 50
    PLAYER_HEIGHT: int = 65
    IMAGE_SCALEX: int = (int(PLAYER_WIDTH * 1.5))
    IMAGE_SCALEY: int = (int(PLAYER_HEIGHT * 1.5))

    # Player spawn
    START_X: int = WIDTH // 2
    START_Y: int = 818 - PLAYER_HEIGHT
    START_LEVEL_INDEX: int = 0
    MAX_LEVEL_INDEX: int = 42

    # Movement constants
    RUN_SPEED: float = 4.0
    ICE_ACCELERATION: float = 0.2
    GHOST_SPEED: int = 15 # this is for testing 
    MAX_FALL_DISTANCE: float = HEIGHT * 0.6
    FALLEN_STUN_TIME: int = 45

    # Platform settings
    NORMAL_FRICTION: float = 1.0
    NORMAL_WIND_PUSH: float = 0.0
    SNOW_WIND_PUSH: float = 0.3
    ICE_FRICTION: float = 0.2
    
    # Jump mechanics
    MIN_JUMP_SPEED: float = 5.0
    MAX_JUMP_SPEED: float = 22.0
    MAX_JUMP_TIMER: int = 30
    JUMP_SPEED_HORIZONTAL: float = 8.0

    # Blizzard settings
    MAX_BLIZZARD_FORCE: float = 0.3
    BLIZZARD_HOLD_TIME: int = 150
    BLIZZARD_ACCELERATION: float = 0.003
    BLIZZARD_IMG_MULTIPLIER: int = 50
    BLIZZARD_INITIAL_DIRECTION: int = -1

    # Collision constants
    COLLISION_SNAP_OFFSET: float = 0.1
    MAX_COLLISION_CHECKS: int = 100
    HYBRID_LOOP_LIMIT: int = 4
    SUBSTEP_MARGIN: int = 40
    RAMP_TIP_PUSH_SPEED: float = 4.0
    RAMP_TIP_IGNORE_FRICTION_FRAMES: int = 10

    # Genetic algorithm parameters
    MAX_GENE_STRENGTH: float = 30.0
    GA_POPULATION_SIZE: int = 500
    GA_GENOME_LENGTH: int = 40
    GA_CROSSOVER_RATE: float = 0.85
    GA_MUTATION_RATE_DIRECTION: float = 0.03
    GA_MUTATION_RATE_TYPE: float = 0.04
    GA_MUTATION_RATE_STRENGTH: float = 0.07
    GA_INITIAL_SIGMA: float = 0.25
    GA_MUTATION_EPSILON: float = 0.005
    GA_MUTATION_STRATEGY: str = "REGRESSIVE" # Options: "PROGRESSIVE", "REGRESSIVE"
    GA_REGRESSIVE_START_DIR: float = 0.042
    GA_REGRESSIVE_START_TYPE: float = 0.085
    GA_REGRESSIVE_START_STRENGTH: float = 0.15
    GA_REGRESSIVE_START_SIGMA: float = 0.535
    GA_REGRESSIVE_DECAY_RATE: float = 0.926
    GA_ELITISM_COUNT: int = 4
    GA_TOURNAMENT_SIZE: int = 6
    GA_STAGNATION_THRESHOLD: int = 5 # try to use 3 here as well
    GA_ALLOW_PROGRESSIVE_GROWTH: bool = True  # False for Phase 1 (Static genome length), True for Phase 2 (Progressive genome growth)
    GA_PROGRESSIVE_START_LENGTH: int = 5
    GA_PROGRESSIVE_GROWTH_AMOUNT: int = 5
    GA_PROGRESSIVE_STAGNATION_THRESHOLD: int = 3
    GA_ACTIVE_SCENARIO: str = "SPEEDRUNNER"  # Options: "REWARDS", "SPEEDRUNNER"
    
    # Coin settings
    COIN_RADIUS: float = 14.0
    PRINCESS_COIN_RADIUS: float = 16.0
    GA_COIN_REWARD_VALUE: float = 500.0
    GA_COIN_PENALTY_VALUE: float = -300.0
    GA_PRINCESS_REWARD_VALUE: float = 10000.0
    GA_DISTANCE_REWARD_MULTIPLIER: float = 1.0 # default to 1 to not influence the coins values
    GA_TIME_PENALTY_VALUE: float = 0.5 
    GA_MAX_TIME_PER_LEVEL: float = 10.0 # Max time for a normal/ice level
    SNOW_TIME: float = 15.0 # Max time for snow blizzard levels
    ALLOW_DRAW: bool = False # draw or not platforms and coins