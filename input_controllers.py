from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Any
from pygame import key, K_LEFT, K_RIGHT, K_SPACE, K_g
from settings import Settings
from ga_models import Genome

@dataclass
class PlayerInput:
    """
    Lightweight data structure containing player control actions.
    Decouples control source (keyboard, network, or Genetic Algorithm AI) from Player physics.
    """
    left: bool = False
    right: bool = False
    jump: bool = False
    ghost: bool = False


class BaseController(ABC):
    """
    Strategy Pattern: Abstract base class for all input controllers.
    """
    @abstractmethod
    def get_input(self, context: Optional[Any] = None) -> PlayerInput:
        """
        Abstract method to retrieve player input signals.

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
    Strategy Pattern: Concrete strategy reading human keyboard inputs via Pygame.
    """
    def reset(self) -> None:
        """
        No-op reset for human keyboard controller.

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
    Strategy Pattern: Dedicated controller executing genes from an agent's Genome.
    Ensures actions synchronize with ground landing state.
    """

    def __init__(self, genome: Optional[Genome]) -> None:
        """
        Initializes controller with a given Genome or generates a random Genome.

        Args:
            genome (Optional[Genome]): Target genome containing gene sequence.
        Returns:
            None
        """
        self.genome: Genome = genome if genome is not None else Genome.random_genome(Settings.GA_GENOME_LENGTH)
        self.gene_index: int = 0
        self.frame_counter: int = 0
        self.is_executing_jump: bool = False
        self.walk_start_x: Optional[float] = None

    def reset(self) -> None:
        """
        Resets controller counters and execution flags for a new episode.

        Args:
            None

        Returns:
            None
        """
        self.gene_index = 0
        self.frame_counter = 0
        self.is_executing_jump = False
        self.walk_start_x = None

    def get_input(self, player: Optional[Any] = None) -> PlayerInput:
        """
        Generates PlayerInput based on current active Gene and Player state.

        Args:
            player (Optional[Any]): Reference to the Player entity for ground state and position tracking.

        Returns:
            PlayerInput: Active control signals dictated by the current gene step.
        """
        if self.gene_index >= len(self.genome.genes):
            return PlayerInput()  # Idle when out of moves

        current_gene = self.genome.genes[self.gene_index]

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
                if self.gene_index >= len(self.genome.genes):
                    return PlayerInput()
                current_gene = self.genome.genes[self.gene_index]

        self.frame_counter += 1
        is_left = (current_gene.direction == -1)
        is_right = (current_gene.direction == 1)

        if current_gene.action_type == "WALK":
            current_x: float = player.current_pos.x if player is not None else 0.0
            if self.walk_start_x is None:
                self.walk_start_x = current_x

            target_px = current_gene.strength
            
            distance_walked = abs(current_x - self.walk_start_x)
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
