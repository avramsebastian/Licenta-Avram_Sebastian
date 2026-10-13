from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any, Dict
from settings import Settings

class FitnessScenario(Enum):
    """
    Phase 1 Scenarios for evaluating fitness functions.
    """
    SCENARIO_1_REWARDS = auto()  # Reward shaping: coins + max height
    SCENARIO_2_SPEEDRUNNER = auto()  # Time penalized: coins + max height - time penalty

class BaseFitnessStrategy(ABC):
    """
    Strategy Pattern: Interface for Phase 1 Fitness Calculation Scenarios.
    """
    __slots__ = ()

    @abstractmethod
    def calculate_fitness(self, agent: Any, time_left: float, max_time: float) -> float:
        """
        Calculates fitness score according to the active Phase 1 scenario rule.

        Args:
            agent (Any): Player agent entity being evaluated.
            time_left (float): Remaining execution time in seconds.
            max_time (float): Maximum total episode duration in seconds.

        Returns:
            float: Computed fitness score (clamped to non-negative floats).
        """
        pass

class RewardsFitnessStrategy(BaseFitnessStrategy):
    """
    Scenario 1: Reward Shaping (Positive/Negative Coin Score + Max Height Reached).
    Formula: ff = coins_score_total + DR * DM
    """
    __slots__ = ()

    def calculate_fitness(self, agent: Any, time_left: float, max_time: float) -> float:
        """
        Calculates Scenario 1 fitness score combining height progress and total coin score.

        Args:
            agent (Any): Player agent entity evaluated.
            time_left (float): Remaining execution time in seconds.
            max_time (float): Maximum total episode duration in seconds.

        Returns:
            float: Fitness score with positive/negative coin reward shaping.
        """
        return agent.coins_score_total + (Settings.GA_DISTANCE_REWARD_MULTIPLIER * agent.max_height_reached)


class SpeedrunnerFitnessStrategy(BaseFitnessStrategy):
    """
    Scenario 2: Time Penalization (Coins Net Score + Max Height - Time Penalty).
    Formula: ff = coins_score_total + DR * DM - TP * (MT - TL)
    """
    __slots__ = ()

    def calculate_fitness(self, agent: Any, time_left: float, max_time: float) -> float:
        """
        Calculates Scenario 2 fitness score combining height progress, positive/negative coin scores, and time penalization.

        Args:
            agent (Any): Player agent entity evaluated.
            time_left (float): Remaining execution time in seconds.
            max_time (float): Maximum total episode duration in seconds.

        Returns:
            float: Fitness score penalized by execution duration.
        """
        elapsed_time = getattr(agent, "finish_time", max_time - time_left)
        return agent.coins_score_total + (Settings.GA_DISTANCE_REWARD_MULTIPLIER * agent.max_height_reached) - (Settings.GA_TIME_PENALTY_VALUE * elapsed_time)


class FitnessStrategyFactory:
    """
    Factory Pattern: Creates and switches between Phase 1 Fitness Strategies dynamically.
    """
    __slots__ = ()
    
    _instances: Dict[FitnessScenario, BaseFitnessStrategy] = {}

    @classmethod
    def create(cls, scenario: FitnessScenario) -> BaseFitnessStrategy:
        """
        Instantiates a concrete BaseFitnessStrategy for the given scenario enum.

        Args:
            scenario (FitnessScenario): Target scenario enumeration key.

        Returns:
            BaseFitnessStrategy: Concrete strategy instance corresponding to scenario.
        """
        if scenario not in cls._instances:
            if scenario is FitnessScenario.SCENARIO_1_REWARDS:
                cls._instances[scenario] = RewardsFitnessStrategy()
            elif scenario is FitnessScenario.SCENARIO_2_SPEEDRUNNER:
                cls._instances[scenario] = SpeedrunnerFitnessStrategy()
            else:
                raise ValueError(f"Unknown Fitness Scenario: {scenario}")
                
        return cls._instances[scenario]