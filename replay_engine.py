from __future__ import annotations
from typing import List, Dict, Any, Optional
from pygame import Surface, K_TAB, draw
from player import Player
from ga_models import Genome, Gene
from input_controllers import AgentController
from settings import Settings
import tkinter as tk
from tkinter import simpledialog

class ReplayEngine:
    """
    Manages the playback of saved Agent runs.
    """

    __slots__ = (
        'is_active', 'runs', 'agents', 'current_level_data_indices', 
        'agent_reported_landing', 'run_completed', 'active_agent_index', 'tab_pressed_last_frame'
    )

    def __init__(self):
        """
        Initializes the ReplayEngine with empty states.
        """
        self.is_active: bool = False
        self.runs: List[Dict[str, Any]] = []
        self.agents: List[Optional[Player]] = []
        self.current_level_data_indices: List[int] = []
        self.agent_reported_landing: List[bool] = []
        self.run_completed: List[bool] = []
        
        self.active_agent_index: int = 0
        self.tab_pressed_last_frame: bool = False

    @property
    def active_agent(self) -> Optional[Player]:
        """
        Returns the currently tracked agent in the replay.
        """
        if not self.agents or self.active_agent_index >= len(self.agents):
            return None
        return self.agents[self.active_agent_index]

    def start_replay(self, loaded_runs: List[Dict[str, Any]]) -> None:
        """
        Initializes the engine with a set of loaded runs and begins playback.
        Prompts the user to select the level index to start the replay from.
        """
        if not loaded_runs:
            print("No runs to replay!")
            return
            
        self.runs = list(loaded_runs)
        
        available_levels: List[int] = []
        for run in self.runs:
            levels_data = run.get("data", {}).get("levels", [])
            for lvl in levels_data:
                l_idx = lvl.get("level_index")
                if l_idx is not None and l_idx not in available_levels:
                    available_levels.append(l_idx)

        if not available_levels:
            max_count = max((len(r.get("data", {}).get("levels", [])) for r in self.runs), default=0)
            if max_count > 0:
                available_levels = list(range(max_count))
            else:
                print("No levels data found in loaded runs to replay!")
                return

        sorted_levels = sorted(available_levels)
        min_lvl = sorted_levels[0]
        max_lvl = sorted_levels[-1]

        selected_level: Optional[int] = min_lvl
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)

            if len(sorted_levels) <= 12:
                lvl_info = f"Available levels: {sorted_levels}"
            else:
                lvl_info = f"Available range: [{min_lvl} - {max_lvl}]"

            prompt_msg = f"Select level index to start replay from:\n{lvl_info}"
            selected_level = simpledialog.askinteger(
                "Select Replay Level",
                prompt_msg,
                parent=root,
                minvalue=min_lvl,
                maxvalue=max_lvl,
                initialvalue=min_lvl
            )
            root.destroy()
        except Exception as err:
            print(f"Dialog unavailable ({err}). Starting from level {min_lvl}.")
            selected_level = min_lvl

        if selected_level is None:
            print("Replay start cancelled.")
            self.stop_replay()
            return

        self.is_active = True
        self.active_agent_index = 0
        
        num_runs = len(self.runs)
        
        self.agents = [None] * num_runs
        self.current_level_data_indices = [0] * num_runs
        self.agent_reported_landing = [False] * num_runs
        self.run_completed = [False] * num_runs
        
        for i in range(num_runs):
            levels_data = self.runs[i].get("data", {}).get("levels", [])
            target_data_idx = 0
            found = False
            for idx, lvl in enumerate(levels_data):
                if lvl.get("level_index") == selected_level:
                    target_data_idx = idx
                    found = True
                    break

            if not found:
                if 0 <= selected_level < len(levels_data):
                    target_data_idx = selected_level
                    found = True

            if not found and levels_data:
                max_run_lvl = max(lvl.get("level_index", 0) for lvl in levels_data)
                if selected_level > max_run_lvl:
                    self.run_completed[i] = True
                    continue

            self.current_level_data_indices[i] = target_data_idx
            self.load_level(i, target_data_idx)

        for idx, comp in enumerate(self.run_completed):
            if not comp:
                self.active_agent_index = idx
                break

        print(f"Replay started at level index {selected_level}!")
        
    def stop_replay(self) -> None:
        """
        Stops playback and clears cached runs and agents.
        """
        self.is_active = False
        self.agents.clear()
        self.runs.clear()

    def load_level(self, run_index: int, level_data_idx: int) -> None:
        """
        Loads the saved gene sequence and spawn configuration for a specific level of a run.
        """
        run = self.runs[run_index]
        levels_data = run.get("data", {}).get("levels", [])
        
        if level_data_idx >= len(levels_data):
            if not self.run_completed[run_index]:
                print(f"Run {run_index + 1} finished!")
                self.run_completed[run_index] = True
            return
            
        level_data = levels_data[level_data_idx]
        
        sx = level_data.get("spawn_x", Settings.START_X)
        sy = level_data.get("spawn_y", Settings.START_Y)
        lvl_idx = level_data.get("level_index", Settings.START_LEVEL_INDEX)
        
        b_force = level_data.get("spawn_blizzard_force", 0.0)
        b_dir = level_data.get("spawn_blizzard_force_dir", Settings.BLIZZARD_INITIAL_DIRECTION)
        b_timer = level_data.get("spawn_blizzard_timer", 0)
        b_snow = level_data.get("spawn_snow_pos", 0.0)

        genes = level_data.get("genes", [])
        genes_list = [
            Gene(
                action_type=g.get("action_type", "WALK"),
                direction=g.get("direction", 1),
                strength=g.get("strength", 0.0)
            ) for g in genes
        ]
        
        genome = Genome(genes=genes_list)
        controller = AgentController(genome)
        
        agent = self.agents[run_index]
        if agent is None:
            agent = Player(sx, sy, controller=controller)
            self.agents[run_index] = agent
        else:
            agent.controller = controller

        agent.reset(
            sx, sy, level_no=lvl_idx,
            blizzard_force=b_force,
            blizzard_force_dir=b_dir,
            blizzard_timer=b_timer,
            snow_pos=b_snow
        )
        
        self.agent_reported_landing[run_index] = False

    def update(self, keys, get_lvl_fn) -> None:
        """
        Advances the replay physics and inputs for all active agents.
        """
        if not self.is_active or not self.agents:
            return
            
        tab_pressed = keys[K_TAB]
        if tab_pressed and not self.tab_pressed_last_frame:
            self.active_agent_index = (self.active_agent_index + 1) % len(self.runs)
        self.tab_pressed_last_frame = tab_pressed
        
        ag_landing = self.agent_reported_landing
        lvl_indices = self.current_level_data_indices
        completed = self.run_completed

        for i, agent in enumerate(self.agents):
            if agent is None:
                continue
                
            env_level = get_lvl_fn(agent.current_level_no)

            if completed[i]:
                agent.handle_input(None)
                agent.update(env_level)
                continue

            controller = agent.controller
            
            if controller:
                if controller.gene_index >= len(controller.genome.genes):
                    if agent.is_on_ground and not agent.is_sliding and not agent.jump_held and agent.jump_timer <= 0:
                        ag_landing[i] = True
                    
            if ag_landing[i]:
                lvl_indices[i] += 1
                self.load_level(i, lvl_indices[i])
                continue

            agent.handle_input(None)
            agent.update(env_level)

    def draw(self, surface: Surface) -> None:
        """
        Renders the active replay agents to the screen.
        """
        if not self.is_active or not self.agents:
            return
            
        active = self.active_agent
        if active is None:
            return
            
        target_level = active.current_level_no
        active_idx = self.active_agent_index
        
        for i, agent in enumerate(self.agents):
            if agent is not None and agent.current_level_no == target_level:
                agent.draw(surface)
                if i == active_idx:
                    draw.rect(surface, (0, 255, 0), agent.rect, 2)