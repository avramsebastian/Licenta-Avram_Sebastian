from __future__ import annotations
from random import sample
from typing import List, Optional, TYPE_CHECKING
from settings import Settings
from ga_models import Gene, Genome
from ga_checkpoint import CheckpointManager
from ga_fitness import FitnessScenario, FitnessStrategyFactory

if TYPE_CHECKING:
    from player import Player


class PopulationManager:
    """
    Manages GA population and evolution.
    """

    def __init__(self) -> None:
        """
        Initializes PopulationManager settings, generation counters, adaptive mutation rates,
        Gaussian mutation deviation sigma, and active fitness calculation strategy.

        Args:
            None

        Returns:
            None
        """
        self.population_size: int = Settings.GA_POPULATION_SIZE
        self.generation_number: int = 1
        self.stagnation_counter: int = 0
        self.best_global_fitness: float = 0.0
        self.current_mutation_rate_dir: float = Settings.GA_MUTATION_RATE_DIRECTION
        self.current_mutation_rate_type: float = Settings.GA_MUTATION_RATE_TYPE
        self.current_mutation_rate_strength: float = Settings.GA_MUTATION_RATE_STRENGTH
        self.current_sigma: float = Settings.GA_INITIAL_SIGMA

        scenario_map = {
            "REWARDS": FitnessScenario.SCENARIO_1_REWARDS,
            "SPEEDRUNNER": FitnessScenario.SCENARIO_2_SPEEDRUNNER,
        }
        
        active_enum = scenario_map.get(Settings.GA_ACTIVE_SCENARIO, FitnessScenario.SCENARIO_1_REWARDS)
        self.fitness_strategy = FitnessStrategyFactory.create(active_enum)

    def reset_evolution(self) -> None:
        """
        Resets stagnation counters, best global fitness, mutation rates, and Gaussian sigma back to settings values.

        Args:
            None

        Returns:
            None
        """
        self.stagnation_counter = 0
        self.best_global_fitness = 0.0
        self.current_mutation_rate_dir = Settings.GA_MUTATION_RATE_DIRECTION
        self.current_mutation_rate_type = Settings.GA_MUTATION_RATE_TYPE
        self.current_mutation_rate_strength = Settings.GA_MUTATION_RATE_STRENGTH
        self.current_sigma = Settings.GA_INITIAL_SIGMA

    def is_generation_finished(self, population: List[Player], checkpoint_manager: Optional[CheckpointManager]) -> bool:
        """
        Determines whether the current generation has completed.
        Returns True if a new Checkpoint Stage was reached OR if all agents are dead/out of moves.

        Args:
            population (List[Player]): List of active AI agent instances.
            checkpoint_manager (Optional[CheckpointManager]): Checkpoint state tracker.

        Returns:
            bool: True if generation is finished, False otherwise.
        """
        if checkpoint_manager is not None and checkpoint_manager.checkpoint_stage_changed:
            return True

        for agent in population:
            if agent.is_alive:
                if hasattr(agent.controller, "gene_index") and hasattr(agent.controller, "genome"):
                    if agent.controller.gene_index < len(agent.controller.genome.genes):
                        return False
        return True

    def evaluate_and_evolve(self, population: List[Player], checkpoint_manager: CheckpointManager) -> List[Genome]:
        """
        Evaluates fitness for all agents in the population and create the next generation's genomes.
        If a new Checkpoint Stage was set, generates fresh random genomes and resets adaptive mutation rates.

        Args:
            population (List[Player]): Current population of evaluated agents.
            checkpoint_manager (CheckpointManager): Active checkpoint manager tracking stage changes.

        Returns:
            List[Genome]: List of evolved Genomes for the next generation.
        """
        for agent in population:
            agent.fitness = self.fitness_strategy.calculate_fitness(agent, time_left=0.0, max_time=0.0)

        sorted_agents = sorted(population, key=lambda a: a.fitness, reverse=True)
        gen_best_fitness = sorted_agents[0].fitness if sorted_agents else 0.0

        if checkpoint_manager.checkpoint_stage_changed:
            checkpoint_manager.checkpoint_stage_changed = False
            self.reset_evolution()
            self.generation_number += 1
            print(f"New level reached {checkpoint_manager.spawn_level + 1}!")
            return [Genome.random_genome(Settings.GA_GENOME_LENGTH) for _ in range(self.population_size)]

        if gen_best_fitness > self.best_global_fitness:
            self.best_global_fitness = gen_best_fitness
            self.stagnation_counter = 0
            self.current_mutation_rate_dir = Settings.GA_MUTATION_RATE_DIRECTION
            self.current_mutation_rate_type = Settings.GA_MUTATION_RATE_TYPE
            self.current_mutation_rate_strength = Settings.GA_MUTATION_RATE_STRENGTH
            self.current_sigma = Settings.GA_INITIAL_SIGMA
            print(f"New best global fitness ({self.best_global_fitness:.1f})!")
        else:
            self.stagnation_counter += 1
            if self.stagnation_counter >= Settings.GA_STAGNATION_THRESHOLD:
                self.current_mutation_rate_dir = min(0.09, self.current_mutation_rate_dir + 0.02)
                self.current_mutation_rate_type = min(0.10, self.current_mutation_rate_type + 0.02)
                self.current_mutation_rate_strength = min(0.15, self.current_mutation_rate_strength + 0.03)
                self.current_sigma = min(0.35, self.current_sigma + 0.05)
                print(f"Stagnation reached! Mutation rates -> Dir: {self.current_mutation_rate_dir:.1%}, Type: {self.current_mutation_rate_type:.1%}, Strength: {self.current_mutation_rate_strength:.1%}, Sigma: {self.current_sigma:.2f}.")
                self.stagnation_counter = 0

        parent_genomes = [agent.controller.genome for agent in sorted_agents]

        if Settings.GA_ALLOW_PROGRESSIVE_GROWTH and self.stagnation_counter >= Settings.GA_STAGNATION_THRESHOLD:
            print(f"Progressive growth! Appending +{Settings.GA_PROGRESSIVE_GROWTH_AMOUNT} genes.")
            for g in parent_genomes:
                g.append_genes(Settings.GA_PROGRESSIVE_GROWTH_AMOUNT)

        next_genomes: List[Genome] = []

        elitism_count = min(Settings.GA_ELITISM_COUNT, len(parent_genomes))
        for i in range(elitism_count):
            elite = Genome(genes=[Gene(g.action_type, g.direction, g.strength) for g in parent_genomes[i].genes])
            next_genomes.append(elite)

        while len(next_genomes) < self.population_size:
            p1 = self._tournament_select(parent_genomes, sorted_agents)
            p2 = self._tournament_select(parent_genomes, sorted_agents)

            c1, c2 = p1.crossover(p2, Settings.GA_CROSSOVER_RATE)
            c1.mutate(self.current_mutation_rate_dir, self.current_mutation_rate_type, self.current_mutation_rate_strength, self.current_sigma)
            c2.mutate(self.current_mutation_rate_dir, self.current_mutation_rate_type, self.current_mutation_rate_strength, self.current_sigma)

            next_genomes.append(c1)
            if len(next_genomes) < self.population_size:
                next_genomes.append(c2)

        self.generation_number += 1
        return next_genomes

    def _tournament_select(self, genomes: List[Genome], sorted_agents: List[Player]) -> Genome:
        """
        Selects a parent Genome via Tournament Selection.

        Args:
            genomes (List[Genome]): Parent genome pool.
            sorted_agents (List[Player]): Evaluated player agents sorted by fitness.

        Returns:
            Genome: Selected parent Genome instance.
        """
        tournament_k = Settings.GA_TOURNAMENT_SIZE
        candidates = sample(list(zip(genomes, sorted_agents)), min(tournament_k, len(genomes)))
        best = max(candidates, key=lambda pair: pair[1].fitness)
        return best[0]
