from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Any
from pygame import key, K_LEFT, K_RIGHT, K_SPACE, K_g
from settings import Settings
from ga_models import Genome
from environment import LevelManager
from ga_architecture import GenomeArchitectureFactory

@dataclass(slots=True)
class PlayerInput:
    """
    Class containing player control actions.
    """
    left: bool = False
    right: bool = False
    jump: bool = False
    ghost: bool = False


class BaseController(ABC):
    """
    Abstract base class for all input controllers.
    """
    __slots__ = ()

    @abstractmethod
    def get_input(self, context: Optional[Any] = None) -> PlayerInput:
        """
        Abstract method to retrieve player input.

        Args:
            context (Optional[Any]): Optional contextual data such as key states or environment references.

        Returns:
            PlayerInput: Data structure containing boolean flags for control actions.
        """
        pass

    def reset(self) -> None:
        """
        Resets controller state for a new generation.

        Args:
            None

        Returns:
            None
        """
        pass


class HumanController(BaseController):
    """
    Strategy reading keyboard inputs.
    """
    __slots__ = ()

    def reset(self) -> None:
        """
        No-op reset for keyboard controller.

        Args:
            None

        Returns:
            None
        """
        pass

    def get_input(self, context: Optional[Any] = None) -> PlayerInput:
        """
        Reads keyboard inputs and maps arrow/space keys to PlayerInput.

        Args:
            context (Optional[Any]): Optional key map sequence. If None, queries key.get_pressed().

        Returns:
            PlayerInput: Populated control actions based on current key presses.
        """
        keys = context if (context is not None and hasattr(context, "__getitem__")) else None
        if keys is None:
            keys = key.get_pressed()

        return PlayerInput(
            left=bool(keys[K_LEFT]),
            right=bool(keys[K_RIGHT]),
            jump=bool(keys[K_SPACE]),
            ghost=bool(keys[K_g])
        )


class AgentController(BaseController):
    """
    Dedicated controller executing genes from an agent's Genome. Plays next action only if player landed.
    """

    __slots__ = ('genome', 'gene_index', 'frame_counter', 'is_executing_jump', 'walk_start_x')

    def __init__(self, genome: Optional[Genome]) -> None:
        """
        Initializes controller with a given Genome or generates a random Genome.

        Args:
            genome (Optional[Genome]): Target genome containing gene sequence.
        Returns:
            None
        """
        if genome is not None:
            self.genome: Genome = genome
        else:
            initial_len = GenomeArchitectureFactory.create().get_initial_length()
            self.genome: Genome = Genome.random_genome(initial_len)
            
        self.gene_index: int = 0
        self.frame_counter: int = 0
        self.is_executing_jump: bool = False
        self.walk_start_x: Optional[float] = None

    @property
    def genes_executed_count(self) -> int:
        """
        Returns the definitive count of genes consumed so far, including
        any gene currently mid-execution (jump in-flight, walk in-progress,
        or jump charging).

        Returns:
            int: Number of genes executed, clamped to [0, len(genome.genes)].
        """
        count = self.gene_index
        if (self.is_executing_jump or
                self.frame_counter > 0 or
                self.walk_start_x is not None):
            count += 1
        return min(max(0, count), len(self.genome.genes))

    def reset(self) -> None:
        """
        Resets controller counters and execution flags for a new gen.

        Args:
            None

        Returns:
            None
        """
        self.gene_index = 0
        self.frame_counter = 0
        self.is_executing_jump = False
        self.walk_start_x = None

    def _is_blocked_by_ascending_ramp(self, player: Any, direction: int) -> bool:
        """
        If player is blocked by asc ramp and wants to walk stop the walk and move to next gene, to not get stuck.

        Args:
            player (Any): Reference to Player entity.
            direction (int): Walk direction (-1 for left, 1 for right).

        Returns:
            bool: True if an ascending ramp is blocking the player in the walk direction, False otherwise.
        """
        current_level_no = getattr(player, "current_level_no", None)
        if current_level_no is None:
            return False

        current_level = LevelManager.get_instance().get_level(current_level_no)
        
        # Cache ramps to avoid repeated attribute lookups
        ramps = getattr(current_level, "ramps", None) if current_level else None
        if not ramps:
            return False

        # Cache player properties locally for fast math
        pos = player.current_pos
        px: float = pos.x
        py: float = pos.y
        p_left: float = px
        p_right: float = px + player.width
        p_top: float = py
        p_bottom: float = py + player.height

        lookahead: float = 15.0
        
        # Pre calculate bounds
        left_bound = p_left - lookahead
        right_bound = p_right + lookahead

        for ramp in ramps:
            rx1, ry1, rx2, ry2 = ramp.x1, ramp.y1, ramp.x2, ramp.y2

            if direction == 1:
                if ry1 > ry2:
                    if (left_bound <= p_right <= rx2 + lookahead) and (p_left < rx2):
                        if p_top < ry1 and ry2 - 5 <= p_bottom <= ry1 + 20:
                            return True
            elif direction == -1:
                if ry2 > ry1:
                    if (rx1 - lookahead <= p_left <= right_bound) and (p_right > rx1):
                        if p_top < ry2 and ry1 - 5 <= p_bottom <= ry2 + 20:
                            return True

        return False

    def get_input(self, player: Optional[Any] = None) -> PlayerInput:
        """
        Generates PlayerInput based on current active Gene and Player state.

        Args:
            player (Optional[Any]): Reference to the Player entity for ground state and position tracking.

        Returns:
            PlayerInput: Active control signals dictated by the current gene step.
        """
        genes = self.genome.genes
        genes_len = len(genes)
        
        if self.gene_index >= genes_len:
            return PlayerInput()  # Idle when out of moves

        is_on_ground = getattr(player, "is_on_ground", True) if player is not None else True

        if not is_on_ground and not self.is_executing_jump:
            return PlayerInput()

        if self.is_executing_jump:
            if not is_on_ground:
                return PlayerInput() 
            else:
                self.is_executing_jump = False
                self.walk_start_x = None
                self.gene_index += 1
                self.frame_counter = 0
                if self.gene_index >= genes_len:
                    return PlayerInput()

        current_gene = genes[self.gene_index]
        self.frame_counter += 1
        
        is_left = (current_gene.direction == -1)
        is_right = (current_gene.direction == 1)

        if current_gene.action_type == "WALK":
            if player is not None and self._is_blocked_by_ascending_ramp(player, current_gene.direction):
                self.walk_start_x = None
                self.gene_index += 1
                self.frame_counter = 0
                return PlayerInput()

            current_x: float = player.current_pos.x if player is not None else 0.0
            if self.walk_start_x is None:
                self.walk_start_x = current_x

            target_px = current_gene.strength
            distance_walked = abs(current_x - self.walk_start_x)

            if self.frame_counter > 3 and distance_walked < 1.0:
                if player is not None and self._is_blocked_by_ascending_ramp(player, current_gene.direction):
                    self.walk_start_x = None
                    self.gene_index += 1
                    self.frame_counter = 0
                    return PlayerInput()

            if distance_walked < target_px and self.frame_counter < 60:
                return PlayerInput(left=is_left, right=is_right, jump=False)
            else:
                self.walk_start_x = None
                self.gene_index += 1
                self.frame_counter = 0
                return PlayerInput()
        else:
            self.walk_start_x = None
            
            charge_duration = min(Settings.MAX_JUMP_TIMER, max(1.0, current_gene.strength))
            
            if self.frame_counter <= charge_duration:
                return PlayerInput(left=is_left, right=is_right, jump=True)
            else:
                self.is_executing_jump = True
                return PlayerInput(left=is_left, right=is_right, jump=False)