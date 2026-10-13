from __future__ import annotations
from random import sample
from typing import List, Optional, TYPE_CHECKING
from operator import attrgetter
from settings import Settings
from ga_models import Genome
from ga_checkpoint import CheckpointManager
from ga_fitness import FitnessScenario, FitnessStrategyFactory
from ga_architecture import GenomeArchitectureFactory
from run_recorder import RunRecorder

if TYPE_CHECKING:
    from player import Player


class PopulationManager:
    """
    Manages GA population and evolution.
    """

    __slots__ = (
        'population_size', 'generation_number', 'stagnation_counter',
        'best_global_fitness', 'overall_best_fitness',
        'current_mutation_rate_dir', 'current_mutation_rate_type',
        'current_mutation_rate_strength', 'current_sigma',
        'generation_frames', 'max_generation_frames',
        'fitness_strategy', 'architecture_strategy'
    )

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
        self.overall_best_fitness: float = 0.0
        
        if Settings.GA_MUTATION_STRATEGY == "REGRESSIVE":
            self.current_mutation_rate_dir = Settings.GA_REGRESSIVE_START_DIR
            self.current_mutation_rate_type = Settings.GA_REGRESSIVE_START_TYPE
            self.current_mutation_rate_strength = Settings.GA_REGRESSIVE_START_STRENGTH
            self.current_sigma = Settings.GA_REGRESSIVE_START_SIGMA
        else:
            self.current_mutation_rate_dir = Settings.GA_MUTATION_RATE_DIRECTION
            self.current_mutation_rate_type = Settings.GA_MUTATION_RATE_TYPE
            self.current_mutation_rate_strength = Settings.GA_MUTATION_RATE_STRENGTH
            self.current_sigma = Settings.GA_INITIAL_SIGMA
            
        self.generation_frames: int = 0
        self.max_generation_frames: int = int(Settings.GA_MAX_TIME_PER_LEVEL * Settings.FPS)

        scenario_map = {
            "REWARDS": FitnessScenario.SCENARIO_1_REWARDS,
            "SPEEDRUNNER": FitnessScenario.SCENARIO_2_SPEEDRUNNER,
        }
        
        active_enum = scenario_map.get(Settings.GA_ACTIVE_SCENARIO, FitnessScenario.SCENARIO_1_REWARDS)
        self.fitness_strategy = FitnessStrategyFactory.create(active_enum)
        self.architecture_strategy = GenomeArchitectureFactory.create()

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
        
        if Settings.GA_MUTATION_STRATEGY == "REGRESSIVE":
            self.current_mutation_rate_dir = Settings.GA_REGRESSIVE_START_DIR
            self.current_mutation_rate_type = Settings.GA_REGRESSIVE_START_TYPE
            self.current_mutation_rate_strength = Settings.GA_REGRESSIVE_START_STRENGTH
            self.current_sigma = Settings.GA_REGRESSIVE_START_SIGMA
        else:
            self.current_mutation_rate_dir = Settings.GA_MUTATION_RATE_DIRECTION
            self.current_mutation_rate_type = Settings.GA_MUTATION_RATE_TYPE
            self.current_mutation_rate_strength = Settings.GA_MUTATION_RATE_STRENGTH
            self.current_sigma = Settings.GA_INITIAL_SIGMA
            
        self.generation_frames = 0

    def get_max_time_for_level(self, level_index: int) -> float:
        """
        Returns max generation time in seconds for the given level.
        Uses Settings.SNOW_TIME for snow levels, and Settings.GA_MAX_TIME_PER_LEVEL for standard levels.

        Args:
            level_index (int): 0-indexed level identifier.

        Returns:
            float: Maximum duration in seconds.
        """
        try:
            from environment import LevelManager
            lvl = LevelManager.get_instance().get_level(level_index)
            if lvl.type == "snow":
                return Settings.SNOW_TIME
        except Exception:
            pass
        return Settings.GA_MAX_TIME_PER_LEVEL

    def is_generation_finished(self, population: List[Player], checkpoint_manager: Optional[CheckpointManager]) -> bool:
        """
        Determines whether the current generation has completed.
        Returns True if a new Checkpoint Stage was reached OR if all agents are dead/out of moves/timer run out.

        Args:
            population (List[Player]): List of active AI agent instances.
            checkpoint_manager (Optional[CheckpointManager]): Checkpoint state tracker.

        Returns:
            bool: True if generation is finished, False otherwise.
        """
        if checkpoint_manager is not None and checkpoint_manager.checkpoint_stage_changed:
            return True

        if Settings.GA_ACTIVE_SCENARIO == "SPEEDRUNNER":
            current_lvl = checkpoint_manager.spawn_level if checkpoint_manager is not None else 0
            max_time = self.get_max_time_for_level(current_lvl)
            self.max_generation_frames = int(max_time * Settings.FPS)
            if self.generation_frames >= self.max_generation_frames:
                return True

        for agent in population:
            if agent.is_alive:
                ctrl = agent.controller
                gene_idx = getattr(ctrl, "gene_index", None)
                if gene_idx is not None and gene_idx < len(ctrl.genome.genes):
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
        current_level_no = checkpoint_manager.spawn_level
        max_time = self.get_max_time_for_level(current_level_no)
        self.max_generation_frames = int(max_time * Settings.FPS)
        time_elapsed = self.generation_frames / Settings.FPS
        time_left = max(0.0, max_time - time_elapsed)
        strategy = self.fitness_strategy

        for agent in population:
            agent.fitness = strategy.calculate_fitness(agent, time_left=time_left, max_time=max_time)

        sorted_agents = sorted(population, key=attrgetter('fitness'), reverse=True)
        gen_best_fitness = sorted_agents[0].fitness if sorted_agents else 0.0
        
        if gen_best_fitness > self.overall_best_fitness:
            self.overall_best_fitness = gen_best_fitness

        is_exhausted = False
        
        if gen_best_fitness >= self.best_global_fitness + 1.0:
            self.best_global_fitness = gen_best_fitness
            self.stagnation_counter = 0
            
            # when progresive reset mutations to baseline on improvement
            if Settings.GA_MUTATION_STRATEGY == "PROGRESSIVE":
                self.current_mutation_rate_dir = Settings.GA_MUTATION_RATE_DIRECTION
                self.current_mutation_rate_type = Settings.GA_MUTATION_RATE_TYPE
                self.current_mutation_rate_strength = Settings.GA_MUTATION_RATE_STRENGTH
                self.current_sigma = Settings.GA_INITIAL_SIGMA
            print(f"New best global fitness ({self.best_global_fitness:.1f})!")
        else:
            if Settings.GA_MUTATION_STRATEGY == "REGRESSIVE":
                is_cooled_down = self.current_mutation_rate_strength <= (Settings.GA_MUTATION_RATE_STRENGTH + Settings.GA_MUTATION_EPSILON)
                if is_cooled_down:
                    self.stagnation_counter += 1
                if self.stagnation_counter >= Settings.GA_PROGRESSIVE_STAGNATION_THRESHOLD:
                    is_exhausted = True

            elif Settings.GA_MUTATION_STRATEGY == "PROGRESSIVE":
                self.stagnation_counter += 1
                is_maxed_out = self.current_mutation_rate_strength >= (Settings.GA_REGRESSIVE_START_STRENGTH - Settings.GA_MUTATION_EPSILON)
                
                if not is_maxed_out:
                    if self.stagnation_counter >= Settings.GA_STAGNATION_THRESHOLD:
                        self.current_mutation_rate_dir = min(Settings.GA_REGRESSIVE_START_DIR, self.current_mutation_rate_dir + 0.02)
                        self.current_mutation_rate_type = min(Settings.GA_REGRESSIVE_START_TYPE, self.current_mutation_rate_type + 0.02)
                        self.current_mutation_rate_strength = min(Settings.GA_REGRESSIVE_START_STRENGTH, self.current_mutation_rate_strength + 0.03)
                        self.current_sigma = min(Settings.GA_REGRESSIVE_START_SIGMA, self.current_sigma + 0.05)
                        self.stagnation_counter = 0
                        print(f"Progressive stagnation! Raise mutation rates -> Dir: {self.current_mutation_rate_dir:.1%}, Type: {self.current_mutation_rate_type:.1%}, Strength: {self.current_mutation_rate_strength:.1%}, Sigma: {self.current_sigma:.2f}.")
                else:
                    if self.stagnation_counter >= Settings.GA_PROGRESSIVE_STAGNATION_THRESHOLD:
                        is_exhausted = True

        # regresive works like SA alg cooling per generation
        if Settings.GA_MUTATION_STRATEGY == "REGRESSIVE" and not is_exhausted:
            decay = Settings.GA_REGRESSIVE_DECAY_RATE
            self.current_mutation_rate_dir = max(Settings.GA_MUTATION_RATE_DIRECTION, self.current_mutation_rate_dir * decay)
            self.current_mutation_rate_type = max(Settings.GA_MUTATION_RATE_TYPE, self.current_mutation_rate_type * decay)
            self.current_mutation_rate_strength = max(Settings.GA_MUTATION_RATE_STRENGTH, self.current_mutation_rate_strength * decay)
            self.current_sigma = max(Settings.GA_INITIAL_SIGMA, self.current_sigma * decay)
            print(f"Regressive cooling applied! Lower mutation rates-> Dir: {self.current_mutation_rate_dir:.1%}, Type: {self.current_mutation_rate_type:.1%}, Strength: {self.current_mutation_rate_strength:.1%}, Sigma: {self.current_sigma:.2f}.")

        if checkpoint_manager.checkpoint_stage_changed:
            checkpoint_manager.checkpoint_stage_changed = False
            self.reset_evolution()
            self.generation_number += 1
            self.generation_frames = 0
            initial_len = self.architecture_strategy.get_initial_length()
            return [Genome.random_genome(initial_len) for _ in range(self.population_size)]

        # Record generation stats before evolving
        average_fitness = sum(a.fitness for a in population) / len(population) if population else 0.0
        current_level_no = checkpoint_manager.spawn_level
        RunRecorder.get_instance().record_generation_stats(
            generation=self.generation_number,
            level_index=current_level_no,
            best_fitness=gen_best_fitness,
            average_fitness=average_fitness,
            mutation_rate_dir=self.current_mutation_rate_dir,
            mutation_rate_type=self.current_mutation_rate_type,
            mutation_rate_strength=self.current_mutation_rate_strength,
            sigma=self.current_sigma,
            genome_length=len(sorted_agents[0].controller.genome.genes) if sorted_agents else Settings.GA_GENOME_LENGTH
        )

        parent_genomes = [agent.controller.genome for agent in sorted_agents]

        if is_exhausted:
            print("Algorithm Exhausted! Resetting mutations.")
            self.stagnation_counter = 0
            
            self.architecture_strategy.handle_exhaustion(parent_genomes)
            
            if Settings.GA_MUTATION_STRATEGY == "REGRESSIVE":
                self.current_mutation_rate_dir = Settings.GA_REGRESSIVE_START_DIR
                self.current_mutation_rate_type = Settings.GA_REGRESSIVE_START_TYPE
                self.current_mutation_rate_strength = Settings.GA_REGRESSIVE_START_STRENGTH
                self.current_sigma = Settings.GA_REGRESSIVE_START_SIGMA
            elif Settings.GA_MUTATION_STRATEGY == "PROGRESSIVE":
                self.current_mutation_rate_dir = Settings.GA_MUTATION_RATE_DIRECTION
                self.current_mutation_rate_type = Settings.GA_MUTATION_RATE_TYPE
                self.current_mutation_rate_strength = Settings.GA_MUTATION_RATE_STRENGTH
                self.current_sigma = Settings.GA_INITIAL_SIGMA

        next_genomes: List[Genome] = []
        elitism_count = min(Settings.GA_ELITISM_COUNT, len(parent_genomes))
        
        for i in range(elitism_count):
            elite = Genome(genes=[g.copy() for g in parent_genomes[i].genes])
            next_genomes.append(elite)

        while len(next_genomes) < self.population_size:
            p1 = self._tournament_select(parent_genomes)
            p2 = self._tournament_select(parent_genomes)

            c1, c2 = p1.crossover(p2, Settings.GA_CROSSOVER_RATE)
            c1.mutate(self.current_mutation_rate_dir, self.current_mutation_rate_type, self.current_mutation_rate_strength, self.current_sigma)
            c2.mutate(self.current_mutation_rate_dir, self.current_mutation_rate_type, self.current_mutation_rate_strength, self.current_sigma)

            next_genomes.append(c1)
            if len(next_genomes) < self.population_size:
                next_genomes.append(c2)

        self.generation_number += 1
        self.generation_frames = 0
        return next_genomes

    def _tournament_select(self, parent_genomes: List[Genome]) -> Genome:
        """
        Selects a parent Genome with Tournament Selection.

        Args:
            parent_genomes (List[Genome]): Parent genome pool (must be sorted by fitness descending).

        Returns:
            Genome: Selected parent Genome instance.
        """
        k = Settings.GA_TOURNAMENT_SIZE
        pool_size = len(parent_genomes)
        
        if k >= pool_size:
            return parent_genomes[0]
            
        best_idx = min(sample(range(pool_size), k))
        return parent_genomes[best_idx]