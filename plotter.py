from __future__ import annotations
import os
import json
import matplotlib
matplotlib.use('Agg')  # to not resize the screen after the plots were saved
import matplotlib.pyplot as plt
from typing import Optional, Dict, Any

class RunPlotter:
    """
    Class responsible for parsing JSON files and generating matplotlib plots.
    """
    _instance: Optional['RunPlotter'] = None
    
    __slots__ = ()

    def __init__(self) -> None:
        pass

    @classmethod
    def get_instance(cls) -> 'RunPlotter':
        if cls._instance is None:
            cls._instance = RunPlotter()
        return cls._instance

    def _load_json(self, filepath: str) -> Dict[str, Any]:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    def plot_level_metrics(self, filepath: str) -> None:
        """
        Plots 2 subplots for a single run:
        1. Level vs Generations Taken
        2. Level vs (Time Taken & Gene Count)
        """
        data = self._load_json(filepath)
        levels_data = data.get("levels")
        
        if not levels_data:
            print(f"No level data found in {filepath}")
            return

        level_indices, generations, times, genes = zip(*(
            (lvl["level_index"], lvl["generations_taken"], lvl["time_taken"], lvl["gene_count"])
            for lvl in levels_data
        ))

        # Plot 1: Difficulty (generations)
        fig1, ax1 = plt.subplots(figsize=(16, 6))
        fig1.suptitle("Run Metrics: Level Difficulty", fontsize=16)

        ax1.plot(level_indices, generations, marker='o', color='b', linestyle='-', linewidth=2)
        ax1.set_xlabel('Level Index', fontsize=12)
        ax1.set_ylabel('Generations Taken', color='b', fontsize=12)
        ax1.grid(True, linestyle='--', alpha=0.7)
        ax1.set_xticks(level_indices)

        fig1.tight_layout()
        
        base_dir = os.path.dirname(filepath)
        base_name = os.path.basename(filepath).replace(".json", "")
        save_path_1 = os.path.join(base_dir, f"{base_name}_difficulty_plot_1.png")
        fig1.savefig(save_path_1)
        plt.close(fig1)
        print(f"Difficulty plot saved to {save_path_1}")

        # Plot 2: Efficiency (time & genes)
        fig2, ax2 = plt.subplots(figsize=(16, 6))
        fig2.suptitle("Run Metrics: Solution Efficiency", fontsize=16)
        
        ax2.set_xlabel('Level Index', fontsize=12)
        
        ax2.plot(level_indices, times, marker='s', color='r', linestyle='-', linewidth=2, label='Time Taken (s)')
        ax2.set_ylabel('Time Taken (Seconds)', color='r', fontsize=12)
        ax2.tick_params(axis='y', labelcolor='r')
        ax2.set_xticks(level_indices)

        ax2_twin = ax2.twinx()
        ax2_twin.plot(level_indices, genes, marker='^', color='g', linestyle='--', linewidth=2, label='Gene Count')
        ax2_twin.set_ylabel('Gene Count', color='g', fontsize=12)
        ax2_twin.tick_params(axis='y', labelcolor='g')

        lines_1, labels_1 = ax2.get_legend_handles_labels()
        lines_2, labels_2 = ax2_twin.get_legend_handles_labels()
        ax2.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper left')

        fig2.tight_layout()
        
        save_path_2 = os.path.join(base_dir, f"{base_name}_efficiency_plot_2.png")
        fig2.savefig(save_path_2)
        plt.close(fig2)
        print(f"Efficiency plot saved to {save_path_2}")

    def plot_level_learning_curve(self, filepath: str, target_level: int) -> None:
        """
        Plots a graph for a specific level's learning curve:
        X-axis: Generation Number
        Y-axis: Average Fitness Score
        """
        data = self._load_json(filepath)
        stats = data.get("generation_stats")
        
        if not stats:
            print(f"No generation stats found for level {target_level} in {filepath}")
            return

        strategy = data.get("experiment_info", {}).get("settings", {}).get("GA_MUTATION_STRATEGY", "UNKNOWN")

        generations = []
        avg_fitness = []
        for s in stats:
            if s.get("level_index") == target_level:
                generations.append(s["generation"])
                avg_fitness.append(s["average_fitness"])
        
        if not generations:
            print(f"No generation stats found for level {target_level} in {filepath}")
            return

        fig, ax1 = plt.subplots(figsize=(10, 6))
        fig.suptitle(f"Learning Curve ({strategy} Strategy)\nLevel {target_level}", fontsize=16)

        ax1.set_xticks(generations)
        ax1.set_xlabel('Generation', fontsize=12)
        ax1.set_ylabel('Fitness Score', color='b', fontsize=12)
        ax1.plot(generations, avg_fitness, color='c', linestyle='-', linewidth=2, label='Average Fitness')
        ax1.tick_params(axis='y', labelcolor='b')
        ax1.grid(True, linestyle='--', alpha=0.5)

        ax1.legend(loc='upper left')

        plt.tight_layout()
        
        base_dir = os.path.dirname(filepath)
        base_name = os.path.basename(filepath).replace(".json", "")
        save_path = os.path.join(base_dir, f"{base_name}_learning_curve_lvl{target_level}_2.png")
        plt.savefig(save_path)
        plt.close(fig)
        print(f"Learning curve plot saved to {save_path}")