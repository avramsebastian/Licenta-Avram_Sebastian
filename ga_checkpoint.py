from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING
from pygame import Rect
from ga_models import Gene

if TYPE_CHECKING:
    from player import Player
    from environment import Level


class CheckpointManager:
    """
    Tracks highest reached platform checkpoint for agent spawning across levels.
    Saves the winning gene sequence of the best agent that reached the checkpoint.
    """

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

    def update_checkpoint(self, player: Player, current_level: Optional[Level]) -> bool:
        """
        Updates spawn origin if player reaches a higher level and lands on a flat platform.
        Saves the best winning route and flags stage transition for fresh genome generation.

        Args:
            player (Player): Player entity instance to evaluate.
            current_level (Optional[Level]): Current active Level object.

        Returns:
            bool: True if a new checkpoint was reached, False otherwise.
        """
        if player.is_on_ground and player.is_alive and not player.is_sliding and not player.is_stunned:
            if current_level is not None and hasattr(current_level, "platform_rects"):
                feet_rect = Rect(player.current_pos.x, player.current_pos.y + player.height, player.width, 4)
                on_flat_platform = any(feet_rect.colliderect(rect) for rect in current_level.platform_rects if rect.width >= 20)
                if not on_flat_platform:
                    return False

            if player.current_level_no > self.spawn_level:
                self.spawn_level = player.current_level_no
                self.spawn_x = player.current_pos.x
                self.spawn_y = player.current_pos.y
                self.best_checkpoint_fitness = player.fitness or getattr(player, "max_height_reached", 0.0)

                if hasattr(player, "controller") and hasattr(player.controller, "genome"):
                    exec_idx = player.controller.gene_index
                    self.best_checkpoint_genes = [
                        Gene(g.action_type, g.direction, g.strength) 
                        for g in player.controller.genome.genes[:exec_idx]
                    ]

                self.checkpoint_stage_changed = True
                print(f"New checkpoint reached! Level: {self.spawn_level}, Pos: ({self.spawn_x:.1f}, {self.spawn_y:.1f}) | Saved agent {len(self.best_checkpoint_genes)} genes!")

                if hasattr(player, "controller") and hasattr(player.controller, "gene_index"):
                    player.controller.gene_index = len(player.controller.genome.genes)
                return True
        return False

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
