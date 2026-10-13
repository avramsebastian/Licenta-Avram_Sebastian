from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from settings import Settings
import tkinter as tk
from tkinter import messagebox


class RunRecorder:
    """
    Records the winning gene slice when a new level spawnpoint is reached
    or when the princess is reached, along with generation counts and run metadata.
    """
    _instance: Optional['RunRecorder'] = None

    __slots__ = (
        'output_dir', 'start_time', 'current_level_start_gen', 
        'level_records', 'generation_stats', 'is_princess_reached'
    )

    def __init__(self, output_dir: str = "saved_runs") -> None:
        """
        Initializes RunRecorder.

        Args:
            output_dir (str): Directory where JSON run logs will be stored.
        """
        self.output_dir: Path = Path(output_dir)
        self.start_time: datetime = datetime.now()
        self.current_level_start_gen: int = 1
        self.level_records: List[Dict[str, Any]] = []
        self.generation_stats: List[Dict[str, Any]] = []
        self.is_princess_reached: bool = False

    @classmethod
    def get_instance(cls, output_dir: str = "saved_runs") -> 'RunRecorder':
        """
        Retrieves or creates the singleton instance of RunRecorder.

        Args:
            output_dir (str): Directory where JSON run logs will be stored.

        Returns:
            RunRecorder: Singleton instance.
        """
        if cls._instance is None:
            cls._instance = RunRecorder(output_dir)
        return cls._instance

    def reset(self) -> None:
        """
        Resets recorder telemetry, clearing saved level records and resetting timers for a fresh run.
        """
        self.start_time = datetime.now()
        self.current_level_start_gen = 1
        self.level_records.clear()
        self.generation_stats.clear()
        self.is_princess_reached = False

    def record_generation_stats(
        self,
        generation: int,
        level_index: int,
        best_fitness: float,
        average_fitness: float,
        mutation_rate_dir: float,
        mutation_rate_type: float,
        mutation_rate_strength: float,
        sigma: float,
        genome_length: int
    ) -> None:
        """
        Records the fitness and mutation stats for a single generation.
        """
        self.generation_stats.append({
            "generation": generation,
            "level_index": level_index,
            "best_fitness": float(best_fitness),
            "average_fitness": float(average_fitness),
            "mutation_rate_dir": float(mutation_rate_dir),
            "mutation_rate_type": float(mutation_rate_type),
            "mutation_rate_strength": float(mutation_rate_strength),
            "sigma": float(sigma),
            "genome_length": int(genome_length)
        })

    def record_level_checkpoint(
        self,
        from_level: int,
        player: Any,
        current_generation: int,
        spawn_x: Optional[float] = None,
        spawn_y: Optional[float] = None,
        time_taken: float = 0.0,
        spawn_blizzard_force: float = 0.0,
        spawn_blizzard_force_dir: int = Settings.BLIZZARD_INITIAL_DIRECTION,
        spawn_blizzard_timer: int = 0,
        spawn_snow_pos: float = 0.0
    ) -> None:
        """
        Records level progression data when the first agent reaches the next level
        and establishes a new spawnpoint.

        Args:
            from_level (int): Level index being completed.
            player (Any): Player agent entity that reached the next level.
            current_generation (int): Current GA generation number.

        Returns:
            None
        """
        if any(rec["level_index"] == from_level for rec in self.level_records):
            return

        controller = getattr(player, "controller", None)
        if controller is None or not hasattr(controller, "genome"):
            return

        exec_count = getattr(controller, "genes_executed_count", None)
        if exec_count is None:
            exec_count = min(max(1, getattr(controller, "gene_index", 0)), len(controller.genome.genes))
        
        active_genes = controller.genome.genes[:exec_count]
        
        generations_taken = max(1, current_generation - self.current_level_start_gen + 1)

        px = spawn_x if spawn_x is not None else getattr(player, "spawn_x", (player.current_pos.x if hasattr(player, "current_pos") else 0.0))
        py = spawn_y if spawn_y is not None else getattr(player, "spawn_y", (player.current_pos.y if hasattr(player, "current_pos") else 0.0))

        level_entry = {
            "level_index": from_level,
            "generations_taken": generations_taken,
            "gene_count": len(active_genes),
            "spawn_x": float(px),
            "spawn_y": float(py),
            "spawn_blizzard_force": float(spawn_blizzard_force),
            "spawn_blizzard_force_dir": int(spawn_blizzard_force_dir),
            "spawn_blizzard_timer": int(spawn_blizzard_timer),
            "spawn_snow_pos": float(spawn_snow_pos),
            "time_taken": float(time_taken),
            "genes": [
                {
                    "index": i,
                    "action_type": g.action_type,
                    "direction": g.direction,
                    "strength": float(g.strength)
                }
                for i, g in enumerate(active_genes)
            ]
        }

        self.level_records.append(level_entry)
        self.current_level_start_gen = current_generation + 1
        print(f"Level {from_level + 1} completed in {generations_taken} generations with {len(active_genes)} genes in {time_taken:.2f}s!")

    def record_princess_reached(
        self,
        player: Any,
        current_generation: int,
        spawn_x: Optional[float] = None,
        spawn_y: Optional[float] = None,
        time_taken: float = 0.0,
        spawn_blizzard_force: float = 0.0,
        spawn_blizzard_force_dir: int = Settings.BLIZZARD_INITIAL_DIRECTION,
        spawn_blizzard_timer: int = 0,
        spawn_snow_pos: float = 0.0
    ) -> bool:
        """
        Records the final level completion when the first agent reaches the Princess.

        Args:
            player (Any): Player agent entity that reached the princess.
            current_generation (int): Current GA generation number.
            spawn_x (Optional[float]): Optional checkpoint spawn X coordinate.
            spawn_y (Optional[float]): Optional checkpoint spawn Y coordinate.

        Returns:
            None
        """
        if self.is_princess_reached:
            return False

        controller = getattr(player, "controller", None)
        if controller is None or not hasattr(controller, "genome"):
            return False

        exec_count = getattr(controller, "genes_executed_count", None)
        if exec_count is None:
            exec_count = min(max(1, getattr(controller, "gene_index", 0)), len(controller.genome.genes))
        
        active_genes = controller.genome.genes[:exec_count]
        
        generations_taken = max(1, current_generation - self.current_level_start_gen + 1)
        current_level_no = getattr(player, "current_level_no", Settings.MAX_LEVEL_INDEX)

        px = spawn_x if spawn_x is not None else getattr(player, "spawn_x", (player.current_pos.x if hasattr(player, "current_pos") else 0.0))
        py = spawn_y if spawn_y is not None else getattr(player, "spawn_y", (player.current_pos.y if hasattr(player, "current_pos") else 0.0))

        level_entry = {
            "level_index": current_level_no,
            "generations_taken": generations_taken,
            "gene_count": len(active_genes),
            "spawn_x": float(px),
            "spawn_y": float(py),
            "spawn_blizzard_force": float(spawn_blizzard_force),
            "spawn_blizzard_force_dir": int(spawn_blizzard_force_dir),
            "spawn_blizzard_timer": int(spawn_blizzard_timer),
            "spawn_snow_pos": float(spawn_snow_pos),
            "time_taken": float(time_taken),
            "genes": [
                {
                    "index": i,
                    "action_type": g.action_type,
                    "direction": g.direction,
                    "strength": float(g.strength)
                }
                for i, g in enumerate(active_genes)
            ]
        }

        self.level_records.append(level_entry)
        self.is_princess_reached = True
        print(f"Princess reached on level {current_level_no} in {generations_taken} generations with {len(active_genes)} genes in {time_taken:.2f}s!")
        return True

    def prompt_and_save(self, game: Any) -> bool:
        """
        Prompts the user a message box whether to save the current run to JSON.
        If confirmed, saves the file and returns True.

        Args:
            game (Any): Active Game instance.

        Returns:
            bool: True if saved, False otherwise.
        """
        should_save = True
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            title = "Save Run"
            
            pm = game.pop_manager
            message = (
                f"Do you want to save the current run?\n\n"
                f"Levels logged: {len(self.level_records)}\n"
                f"Current generation: {pm.generation_number}"
            )
            should_save = messagebox.askyesno(title, message)
            root.destroy()
        except Exception as err:
            print(f"Dialog unavailable ({err}). Saving automatically.")
            should_save = True

        if should_save:
            filepath = self.save_to_json(game)
            if filepath:
                print(f"Successfully saved run to: {filepath}")
            return True
        else:
            print("Save cancelled.")
            return False

    def save_to_json(self, game: Any) -> Optional[str]:
        """
        Serializes all data to a JSON file.

        Args:
            game (Any): Active Game instance.

        Returns:
            Optional[str]: Filepath string of saved JSON, or None if error.
        """
        try:
            phase = "2" if Settings.GA_ALLOW_PROGRESSIVE_GROWTH else "1"
            fitness_char = "R" if Settings.GA_ACTIVE_SCENARIO == "REWARDS" else "S"
            mutation_char = "P" if Settings.GA_MUTATION_STRATEGY == "PROGRESSIVE" else "R"
            
            timestamp_str = datetime.now().strftime("%d_%H_%M")
            run_name = f"{phase}_{fitness_char}_{mutation_char}_{timestamp_str}"
            
            run_dir = self.output_dir / run_name
            run_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"{run_name}.json"
            filepath = run_dir / filename

            elapsed_seconds = (datetime.now() - self.start_time).total_seconds()
            hours = int(elapsed_seconds // 3600)
            minutes = int((elapsed_seconds % 3600) // 60)
            seconds = int(elapsed_seconds % 60)
            
            if hours > 0:
                total_time_str = f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                total_time_str = f"{minutes}m {seconds}s"
            else:
                total_time_str = f"{seconds}s"

            pm = game.pop_manager
            cp = game.checkpoint_manager
            
            best_fitness = max(
                float(pm.overall_best_fitness),
                float(pm.best_global_fitness),
                float(cp.best_checkpoint_fitness)
            )

            settings_dict = {
                "GA_POPULATION_SIZE": Settings.GA_POPULATION_SIZE,
                "GA_GENOME_LENGTH": Settings.GA_GENOME_LENGTH,
                "GA_CROSSOVER_RATE": Settings.GA_CROSSOVER_RATE,
                "GA_ELITISM_COUNT": Settings.GA_ELITISM_COUNT,
                "GA_TOURNAMENT_SIZE": Settings.GA_TOURNAMENT_SIZE,
                "GA_STAGNATION_THRESHOLD": Settings.GA_STAGNATION_THRESHOLD,
                "GA_ALLOW_PROGRESSIVE_GROWTH": Settings.GA_ALLOW_PROGRESSIVE_GROWTH,
                "GA_ACTIVE_SCENARIO": Settings.GA_ACTIVE_SCENARIO,
                "GA_MUTATION_STRATEGY": Settings.GA_MUTATION_STRATEGY,
                "GA_MAX_TIME_PER_LEVEL": Settings.GA_MAX_TIME_PER_LEVEL,
                "SNOW_TIME": Settings.SNOW_TIME,
                "ALLOW_DRAW": Settings.ALLOW_DRAW
            }

            if settings_dict["GA_MUTATION_STRATEGY"] == "PROGRESSIVE":
                settings_dict.update({
                    "GA_MUTATION_RATE_DIRECTION": Settings.GA_MUTATION_RATE_DIRECTION,
                    "GA_MUTATION_RATE_TYPE": Settings.GA_MUTATION_RATE_TYPE,
                    "GA_MUTATION_RATE_STRENGTH": Settings.GA_MUTATION_RATE_STRENGTH,
                    "GA_INITIAL_SIGMA": Settings.GA_INITIAL_SIGMA,
                })
            else:
                settings_dict.update({
                    "GA_REGRESSIVE_START_DIR": Settings.GA_REGRESSIVE_START_DIR,
                    "GA_REGRESSIVE_START_TYPE": Settings.GA_REGRESSIVE_START_TYPE,
                    "GA_REGRESSIVE_START_STRENGTH": Settings.GA_REGRESSIVE_START_STRENGTH,
                    "GA_REGRESSIVE_START_SIGMA": Settings.GA_REGRESSIVE_START_SIGMA,
                    "GA_REGRESSIVE_DECAY_RATE": Settings.GA_REGRESSIVE_DECAY_RATE,
                })

            data = {
                "experiment_info": {
                    "start_time": self.start_time.isoformat(),
                    "total_time_took": total_time_str,
                    "total_generations": pm.generation_number,
                    "best_global_fitness": round(best_fitness, 2),
                    "experiment_finished": getattr(game, "experiment_finished", False),
                    "settings": settings_dict
                },
                "levels": self.level_records,
                "generation_stats": self.generation_stats
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

            return str(filepath)
        except Exception as e:
            print(f"Error saving run: {e}")
            return None