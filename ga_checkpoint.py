from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING
from pygame import Rect
from ga_models import Gene
from settings import Settings
from run_recorder import RunRecorder
from environment import LevelManager

if TYPE_CHECKING:
    from player import Player
    from environment import Level

class _MockGenome:
    __slots__ = ('genes',)
    def __init__(self, genes: List[Gene]):
        self.genes = genes

class _MockController:
    __slots__ = ('genome', 'gene_index', 'is_executing_jump')
    def __init__(self, genes: List[Gene]):
        self.genome = _MockGenome(genes)
        self.gene_index = len(genes)
        self.is_executing_jump = False

class _MockPlayer:
    __slots__ = ('controller',)
    def __init__(self, genes: List[Gene]):
        self.controller = _MockController(genes)


class CheckpointManager:
    """
    Tracks highest reached platform checkpoint for agent spawning across levels.
    Saves the winning gene sequence of the best agent that reached the checkpoint.
    """

    __slots__ = (
        'spawn_x', 'spawn_y', 'spawn_level', 'best_checkpoint_genes',
        'best_checkpoint_fitness', 'checkpoint_stage_changed',
        'spawn_blizzard_force', 'spawn_blizzard_force_dir',
        'spawn_blizzard_timer', 'spawn_snow_pos'
    )

    def __init__(self, start_x: float, start_y: float, start_level: int = 0) -> None:
        """
        Initializes CheckpointManager with initial spawn coordinates and level.

        Args:
            start_x (float): Initial horizontal spawn position.
            start_y (float): Initial vertical spawn position.
            start_level (int): Initial spawn level index. Defaults to 0.

        Returns:
            None
        """
        self.spawn_x: float = start_x
        self.spawn_y: float = start_y
        self.spawn_level: int = start_level
        self.best_checkpoint_genes: List[Gene] = []
        self.best_checkpoint_fitness: float = -1.0
        self.checkpoint_stage_changed: bool = False

        self.spawn_blizzard_force: float = 0.0
        self.spawn_blizzard_force_dir: int = Settings.BLIZZARD_INITIAL_DIRECTION
        self.spawn_blizzard_timer: int = 0
        self.spawn_snow_pos: float = 0.0

    def update_checkpoint(
        self, 
        player: Player, 
        current_level: Optional[Level], 
        current_generation: int = 1, 
        generation_frames: int = 0
    ) -> bool:
        """
        Updates spawn origin if player reaches a higher level and lands on a flat platform.
        Saves the best winning route and flags stage transition for new genome generation for all agents.

        Args:
            player (Player): Player entity instance to evaluate.
            current_level (Optional[Level]): Current active Level object.
            current_generation (int): Current GA generation number.
            generation_frames (int): Number of frames the current generation has been running.

        Returns:
            bool: True if a new checkpoint was reached, False otherwise.
        """
        if player.current_level_no <= self.spawn_level:
            return False

        if not player.is_on_ground or not player.is_alive or player.is_sliding or player.is_stunned:
            return False

        actual_level = LevelManager.get_instance().get_level(player.current_level_no)
        target_level = actual_level if actual_level is not None else current_level

        # Check if player landed on a valid flat platform
        if target_level is not None and hasattr(target_level, "platform_rects"):
            feet_rect = Rect(player.current_pos.x, player.current_pos.y + player.height, player.width, 4)
            
            on_flat_platform = False
            for rect in target_level.platform_rects:
                if rect.width >= 20 and feet_rect.colliderect(rect):
                    on_flat_platform = True
                    break
                    
            if not on_flat_platform:
                return False

        extracted_genes = []
        controller = getattr(player, "controller", None)
        
        if controller is not None and hasattr(controller, "genome"):
            
            exec_count = getattr(controller, "genes_executed_count", None)
            if exec_count is None:
                exec_count = min(max(1, getattr(controller, "gene_index", 0)), len(controller.genome.genes))
            
            extracted_genes = [
                Gene(g.action_type, g.direction, g.strength) 
                for g in controller.genome.genes[:exec_count]
            ]

        current_fitness = getattr(player, "fitness", 0.0) or getattr(player, "max_height_reached", 0.0)
        time_taken = generation_frames / Settings.FPS

        # Cache transition state
        from_level = self.spawn_level
        start_x_for_level = self.spawn_x
        start_y_for_level = self.spawn_y
        start_blizzard_force = self.spawn_blizzard_force
        start_blizzard_force_dir = self.spawn_blizzard_force_dir
        start_blizzard_timer = self.spawn_blizzard_timer
        start_snow_pos = self.spawn_snow_pos
        
        self.spawn_level = player.current_level_no
        self.spawn_x = player.current_pos.x
        self.spawn_y = player.current_pos.y
        self.best_checkpoint_fitness = current_fitness
        self.best_checkpoint_genes = extracted_genes
        
        self.spawn_blizzard_force = player.blizzard_force
        self.spawn_blizzard_force_dir = player.blizzard_force_dir
        self.spawn_blizzard_timer = player.blizzard_timer
        self.spawn_snow_pos = player.snow_pos

        self.checkpoint_stage_changed = True

        mock_player = _MockPlayer(self.best_checkpoint_genes)
        
        RunRecorder.get_instance().record_level_checkpoint(
            from_level=from_level,
            player=mock_player,
            current_generation=current_generation,
            spawn_x=start_x_for_level,
            spawn_y=start_y_for_level,
            time_taken=time_taken,
            spawn_blizzard_force=start_blizzard_force,
            spawn_blizzard_force_dir=start_blizzard_force_dir,
            spawn_blizzard_timer=start_blizzard_timer,
            spawn_snow_pos=start_snow_pos
        )

        if controller is not None and hasattr(controller, "gene_index"):
            controller.gene_index = len(controller.genome.genes)
            
        return True

    def reset(self, default_x: float, default_y: float, default_level: int = 0) -> None:
        """
        Resets checkpoint manager to initial starting parameters.

        Args:
            default_x (float): Default starting horizontal position.
            default_y (float): Default starting vertical position.
            default_level (int): Default starting level index. Defaults to 0.

        Returns:
            None
        """
        self.spawn_x = default_x
        self.spawn_y = default_y
        self.spawn_level = default_level
        self.best_checkpoint_genes = []
        self.best_checkpoint_fitness = -1.0
        self.checkpoint_stage_changed = False

        self.spawn_blizzard_force = 0.0
        self.spawn_blizzard_force_dir = Settings.BLIZZARD_INITIAL_DIRECTION
        self.spawn_blizzard_timer = 0
        self.spawn_snow_pos = 0.0