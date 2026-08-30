from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any, Dict
from settings import Settings

class FitnessScenario(Enum):
    """
    Phase 1 Scenarios for evaluating fitness functions.
    """
    SCENARIO_1_REWARDS = auto()  # Reward Shaping: Coins + Max Height
    SCENARIO_2_SPEEDRUNNER = auto()  # Time Penalized: Coins + Max Height - Time Penalty

class BaseFitnessStrategy(ABC):
    """
    Strategy Pattern: Interface for Phase 1 Fitness Calculation Scenarios.
    """

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
    Scenario 1: Reward Shaping (Positive/Negative Coin Net Score + Max Height Reached).
    Formula: ff = coins_score_total + DR * DM
    """

    def calculate_fitness(self, agent: Any, time_left: float, max_time: float) -> float:
        """
        Calculates Scenario 1 fitness score combining height progress and total coin score (positive bonuses & negative penalties).

        Args:
            agent (Any): Player agent entity evaluated.
            time_left (float): Remaining execution time in seconds.
            max_time (float): Maximum total episode duration in seconds.

        Returns:
            float: Fitness score with positive/negative coin reward shaping.
        """
        dm = getattr(agent, "max_height_reached", 0.0)
        coins_score = getattr(agent, "coins_score_total", 0.0)
        return coins_score + (Settings.GA_DISTANCE_REWARD_MULTIPLIER * dm)


class SpeedrunnerFitnessStrategy(BaseFitnessStrategy):
    """
    Scenario 2: Time Penalization (Coins Net Score + Max Height - Time Penalty).
    Formula: ff = coins_score_total + DR * DM - TP * (MT - TL)
    """

    def calculate_fitness(self, agent: Any, time_left: float, max_time: float) -> float:
        """
        Calculates Scenario 1 fitness score combining height progress, positive/negative coin scores, and time penalization.

        Args:
            agent (Any): Player agent entity evaluated.
            time_left (float): Remaining execution time in seconds.
            max_time (float): Maximum total episode duration in seconds.

        Returns:
            float: Fitness score penalized by execution duration.
        """
        dm = getattr(agent, "max_height_reached", 0.0)
        coins_score = getattr(agent, "coins_score_total", 0.0)
        elapsed_time = max_time - time_left
        return coins_score + (Settings.GA_DISTANCE_REWARD_MULTIPLIER * dm) - (Settings.GA_TIME_PENALTY_VALUE * elapsed_time)


class FitnessStrategyFactory:
    """
    Factory Pattern: Creates and switches between Phase 1 Fitness Strategies dynamically.
    """
    
    _strategies: Dict[FitnessScenario, type] = {
        FitnessScenario.SCENARIO_1_REWARDS: RewardsFitnessStrategy,
        FitnessScenario.SCENARIO_2_SPEEDRUNNER: SpeedrunnerFitnessStrategy,
    }

    @classmethod
    def create(cls, scenario: FitnessScenario) -> BaseFitnessStrategy:
        """
        Instantiates a concrete BaseFitnessStrategy for the given scenario enum.

        Args:
            scenario (FitnessScenario): Target scenario enumeration key.

        Returns:
            BaseFitnessStrategy: Concrete strategy instance corresponding to scenario.
        """
        strategy_cls = cls._strategies.get(scenario)
        if strategy_cls is None:
            raise ValueError(f"Unknown Fitness Scenario: {scenario}")
        return strategy_cls()
