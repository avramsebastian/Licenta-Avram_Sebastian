from __future__ import annotations
from typing import List, Optional, Dict, Any
from random import uniform
from pygame import Surface, Rect, Clock, display, event as pygame_event, KEYDOWN, QUIT, K_r, K_t, K_p, K_o, K_c, K_s, key
from settings import Settings
from assets import AssetsManager
from player import Player
from environment import LevelManager, Level
from input_controllers import HumanController, AgentController
from ga_models import Genome, Gene, JUMP_BOUNDS
from ga_checkpoint import CheckpointManager
from ga_population import PopulationManager
from ga_architecture import GenomeArchitectureFactory
from run_recorder import RunRecorder
from menu_screen import MenuScreen
from stats_screen import StatsScreen
from replay_screen import ReplayScreen
from replay_engine import ReplayEngine
from plotter import RunPlotter
from colors import Colors
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from pathlib import Path
import json
import sys


class Game:
    """
    The main Engine class that handles the window, event polling,
    the core game loop, collision detection, rendering, level transitions,
    and automated Genetic Algorithm generation lifecycle.
    """

    __slots__ = (
        'screen', 'clock', 'running', 'frame_counter', 'snow_image',
        'level_manager', 'current_level', 'checkpoint_manager', 'pop_manager',
        'human_player', 'test_agent', 'test_agent_reported_landing',
        'population', 'experiment_finished', 'stats_screen', 'replay_screen',
        'replay_engine', 'menu_screen'
    )

    def __init__(self) -> None:
        """
        Initializes display, clock, asset manager, level manager,
        and spawns a population of AI Agent players.

        Args:
            None

        Returns:
            None
        """
        self.screen: Surface = display.set_mode((Settings.WIDTH, Settings.HEIGHT))
        self.clock: Clock = Clock()
        self.running: bool = True
        self.frame_counter: int = 0

        AssetsManager.get_instance().load_assets()
        self.snow_image: Optional[Surface] = AssetsManager.get_instance().get_snow_image()

        self.level_manager: LevelManager = LevelManager(Settings.LEVEL_DATA_PATH)
        self.current_level: Level = self.level_manager.get_current_level()

        self.checkpoint_manager: CheckpointManager = CheckpointManager(Settings.START_X, Settings.START_Y, Settings.START_LEVEL_INDEX)

        self.pop_manager: PopulationManager = PopulationManager()

        self.human_player: Optional[Player] = None

        self.test_agent: Optional[Player] = None
        self.test_agent_reported_landing: bool = False

        self.population: List[Player] = []
        for _ in range(self.pop_manager.population_size):
            controller = AgentController(Genome.random_genome(length=GenomeArchitectureFactory.create().get_initial_length()))
            agent = Player(Settings.START_X, Settings.START_Y, controller=controller)
            agent.current_level_no = self.level_manager.current_level_index
            self.population.append(agent)

        if self.population:
            sample_genome = self.population[0].controller.genome
            if sample_genome.genes:
                gene_bytes = sys.getsizeof(sample_genome.genes[0])
                list_bytes = sys.getsizeof(sample_genome.genes) + gene_bytes * len(sample_genome.genes)
                print(f"Size of a single gene: {gene_bytes} bytes")
                print(f"Size of a list of genes for an agent: {list_bytes / 1024:.2f} KB")

        self.experiment_finished: bool = False

        self.stats_screen: StatsScreen = StatsScreen.get_instance(on_back=self.on_stats_back)

        self.replay_screen: ReplayScreen = ReplayScreen.get_instance(
            on_back=self.on_replay_back,
            on_start=self.start_replay
        )
        
        self.replay_engine: ReplayEngine = ReplayEngine()
        self.menu_screen: MenuScreen = MenuScreen(
            on_replay=self.open_replay_screen,
            on_load=self.open_load_run_dialog,
            on_plot=self.open_plot_dialog,
            on_exit=self.exit_game
        )

    def exit_game(self) -> None:
        """
        Exits and terminates the game application.
        """
        self.running = False

    def open_load_run_dialog(self) -> None:
        """
        Prompts user to select a saved run JSON file from the saved_runs folder.
        Loads the run data and displays it on the StatsScreen.
        """
        chosen_file = None
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            initial_dir = Path("saved_runs").resolve()
            if not initial_dir.exists():
                initial_dir.mkdir(parents=True, exist_ok=True)
            chosen_file = filedialog.askopenfilename(
                initialdir=str(initial_dir),
                title="Select Saved Run JSON",
                filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
            )
            root.destroy()
        except Exception as e:
            print(f"Error opening file dialog: {e}")

        if chosen_file:
            try:
                with open(chosen_file, "r", encoding="utf-8") as f:
                    run_data = json.load(f)
                self.menu_screen.hide()
                self.stats_screen.on_back = self.on_stats_back
                self.stats_screen.show(run_data)
            except Exception as e:
                print(f"Error loading run JSON '{chosen_file}': {e}")

    def open_plot_dialog(self) -> None:
        """
        Prompts user to select a saved run JSON file, asks for a target level to generate learning curve plot.
        """
        chosen_file = None
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            initial_dir = Path("saved_runs").resolve()
            if not initial_dir.exists():
                initial_dir.mkdir(parents=True, exist_ok=True)
            chosen_file = filedialog.askopenfilename(
                initialdir=str(initial_dir),
                title="Select Saved Run JSON to Plot",
                filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
            )
            
            if chosen_file:
                target_level = simpledialog.askinteger(
                    "Plot Learning Curve", 
                    "Which level would you like to plot the learning curve for?",
                    parent=root,
                    minvalue=1,
                    maxvalue=43
                )
                if target_level is not None:
                    try:
                        plotter = RunPlotter.get_instance()
                        plotter.plot_level_metrics(chosen_file)
                        plotter.plot_level_learning_curve(chosen_file, target_level)
                        messagebox.showinfo("Success", f"Plots successfully saved in the same folder as the JSON file!")
                    except Exception as e:
                        messagebox.showerror("Plotting Error", f"Failed to generate plots: {e}")

            root.destroy()
        except Exception as e:
            print(f"Error opening plot dialog: {e}")

    def on_stats_back(self) -> None:
        """
        Navigation callback from StatsScreen back to MenuScreen.
        """
        self.menu_screen.show()

    def open_replay_screen(self) -> None:
        """
        Opens the Replay Screen and hides the Menu Screen.
        """
        self.menu_screen.hide()
        self.replay_screen.show()

    def on_replay_back(self) -> None:
        """
        Navigation callback from ReplayScreen back to MenuScreen.
        """
        self.menu_screen.show()

    def start_replay(
        self,
        loaded_runs: List[Dict[str, Any]]
    ) -> None:
        """
        Starts replay simulation with the given loaded runs data and optional custom spawn coordinates.
        """
        self.experiment_finished = False
        self.population.clear()
        
        self.replay_engine.start_replay(loaded_runs)
        self.replay_screen.hide()

        if not self.replay_engine.is_active:
            print("No levels data in loaded runs to replay!")
            self.menu_screen.show()
            return

        if self.replay_engine.active_agent is not None:
            self.level_manager.current_level_index = self.replay_engine.active_agent.current_level_no
            self.current_level = self.level_manager.get_current_level()

    def handle_events(self) -> None:
        """
        Processes window events.
        - Press 'R' to reset and respawn all AI Agents with fresh random genomes.
        - Press 'T' to spawn/reset a Human-controlled Player for testing!
        - Press 'P' to despawn all AI population agents!
        - Press 'O' to spawn/despawn a single test AI agent with customizable action type, direction, and strength!

        Args:
            None

        Returns:
            None
        """
        cp = self.checkpoint_manager

        for event in pygame_event.get():
            if event.type == QUIT:
                self.running = False
                return

            if self.stats_screen.is_active:
                if self.stats_screen.handle_event(event):
                    continue

            if self.replay_screen.is_active:
                if self.replay_screen.handle_event(event):
                    continue

            if self.menu_screen.is_active:
                if self.menu_screen.handle_event(event):
                    continue
                if event.type == KEYDOWN and event.key == K_c and not self.experiment_finished:
                    self.menu_screen.hide()
                    continue

            if event.type == KEYDOWN:
                if event.key == K_c:
                    if self.replay_engine.is_active:
                        self.replay_engine.stop_replay()
                    self.menu_screen.toggle()
                    continue
                elif event.key == K_s:
                    RunRecorder.get_instance().prompt_and_save(self)
                    continue
                elif event.key == K_r:
                    if self.replay_engine.is_active:
                        continue
                    self.experiment_finished = False
                    self.menu_screen.hide()
                    self.pop_manager.reset_evolution()
                    RunRecorder.get_instance().reset()

                    if self.human_player is not None and self.human_player.is_alive:
                        spawn_x = self.human_player.current_pos.x
                        spawn_y = self.human_player.current_pos.y
                        spawn_level = self.human_player.current_level_no
                        b_force = self.human_player.blizzard_force
                        b_dir = self.human_player.blizzard_force_dir
                        b_timer = self.human_player.blizzard_timer
                        b_snow = self.human_player.snow_pos
                    else:
                        spawn_x = cp.spawn_x
                        spawn_y = cp.spawn_y
                        spawn_level = cp.spawn_level
                        b_force = cp.spawn_blizzard_force
                        b_dir = cp.spawn_blizzard_force_dir
                        b_timer = cp.spawn_blizzard_timer
                        b_snow = cp.spawn_snow_pos
                    
                    if not self.population:
                        for _ in range(self.pop_manager.population_size):
                            controller = AgentController(Genome.random_genome(length=GenomeArchitectureFactory.create().get_initial_length()))
                            agent = Player(spawn_x, spawn_y, controller=controller)
                            agent.current_level_no = spawn_level
                            agent.blizzard_force = b_force
                            agent.blizzard_force_dir = b_dir
                            agent.blizzard_timer = b_timer
                            agent.snow_pos = b_snow
                            self.population.append(agent)
                    else:
                        for agent in self.population:
                            agent.controller = AgentController(Genome.random_genome(length=GenomeArchitectureFactory.create().get_initial_length()))
                            agent.reset(
                                spawn_x,
                                spawn_y,
                                level_no=spawn_level,
                                blizzard_force=b_force,
                                blizzard_force_dir=b_dir,
                                blizzard_timer=b_timer,
                                snow_pos=b_snow,
                            )

                    print(f"Reset Agents!")
                elif event.key == K_t:
                    if self.replay_engine.is_active:
                        continue
                    if self.human_player is None:
                        spawn_x = cp.spawn_x
                        spawn_y = cp.spawn_y
                        spawn_level = cp.spawn_level
                        self.human_player = Player(spawn_x, spawn_y, controller=HumanController())
                        self.human_player.current_level_no = spawn_level
                        self.human_player.blizzard_force = cp.spawn_blizzard_force
                        self.human_player.blizzard_force_dir = cp.spawn_blizzard_force_dir
                        self.human_player.blizzard_timer = cp.spawn_blizzard_timer
                        self.human_player.snow_pos = cp.spawn_snow_pos
                        print(f"Spawned Test Player at Level {spawn_level + 1}!")
                    else:
                        self.human_player = None
                        print("Despawned Test Player!")
                elif event.key == K_p:
                    if self.replay_engine.is_active:
                        continue
                    self.population.clear()
                    self.test_agent = None
                    print("Despawned all agents!")
                elif event.key == K_o:
                    if self.replay_engine.is_active:
                        continue
                    if self.test_agent is not None:
                        self.test_agent = None
                        self.test_agent_reported_landing = False
                        print("Despawned Single Test Agent!")
                    else:
                        print("Single test agent configuration!")
                        if self.human_player is not None and self.human_player.is_alive:
                            default_x = self.human_player.current_pos.x
                            default_y = self.human_player.current_pos.y
                            default_level = self.human_player.current_level_no
                            b_force = self.human_player.blizzard_force
                            b_dir = self.human_player.blizzard_force_dir
                            b_timer = self.human_player.blizzard_timer
                            b_snow = self.human_player.snow_pos
                        else:
                            default_x = cp.spawn_x
                            default_y = cp.spawn_y
                            default_level = cp.spawn_level
                            b_force = cp.spawn_blizzard_force
                            b_dir = cp.spawn_blizzard_force_dir
                            b_timer = cp.spawn_blizzard_timer
                            b_snow = cp.spawn_snow_pos

                        try:
                            x_in = input(f"Spawn X (or 'X Y', default {default_x:.1f}): ").strip()
                            if x_in:
                                parts = x_in.replace(",", " ").split()
                                spawn_x = float(parts[0])
                                if len(parts) > 1:
                                    spawn_y = float(parts[1])
                                else:
                                    y_in = input(f"Spawn Y (default {default_y:.1f}): ").strip()
                                    spawn_y = float(y_in) if y_in else default_y
                                if len(parts) > 2:
                                    spawn_level = max(0, int(parts[2]) - 1)
                                else:
                                    lvl_in = input(f"Spawn Level [1-{Settings.MAX_LEVEL_INDEX + 1}] (default {default_level + 1}): ").strip()
                                    spawn_level = max(0, int(lvl_in) - 1) if lvl_in else default_level
                            else:
                                spawn_x = default_x
                                y_in = input(f"Spawn Y (default {default_y:.1f}): ").strip()
                                spawn_y = float(y_in) if y_in else default_y
                                lvl_in = input(f"Spawn Level [1-{Settings.MAX_LEVEL_INDEX + 1}] (default {default_level + 1}): ").strip()
                                spawn_level = max(0, int(lvl_in) - 1) if lvl_in else default_level

                            act_in = input("Action type (JL = Low [3-6], JM = Med [17-22], JH = High [25-30], W = Walk, default JH): ").strip().upper()
                            if act_in.startswith("JL"): action_type = "JUMP_LOW"
                            elif act_in.startswith("JM"): action_type = "JUMP_MEDIUM"
                            elif act_in.startswith("W"): action_type = "WALK"
                            else: action_type = "JUMP_HIGH"

                            dir_in = input("Direction (-1 = Left, 1 = Right, default 1): ").strip()
                            direction = -1 if dir_in == "-1" else 1

                            min_s, max_s = JUMP_BOUNDS.get(action_type, (1.0, 30.0))
                            str_in = input(f"Jump/Walk Strength range: [{min_s:.1f}, {max_s:.1f}]): ").strip()
                            if str_in:
                                strength = float(str_in)
                            else:
                                strength = uniform(min_s, max_s)
                        except Exception as err:
                            min_s, max_s = JUMP_BOUNDS.get("JUMP_HIGH", (25.0, 30.0))
                            action_type, direction, strength = "JUMP_HIGH", 1, uniform(min_s, max_s)
                            spawn_x, spawn_y, spawn_level = default_x, default_y, default_level

                        test_gene = Gene(action_type=action_type, direction=direction, strength=strength)
                        test_genome = Genome(genes=[test_gene])
                        self.test_agent = Player(spawn_x, spawn_y, controller=AgentController(test_genome))
                        self.test_agent.current_level_no = spawn_level
                        self.test_agent.blizzard_force = b_force
                        self.test_agent.blizzard_force_dir = b_dir
                        self.test_agent.blizzard_timer = b_timer
                        self.test_agent.snow_pos = b_snow
                        self.test_agent_reported_landing = False
                        print(f"Spawned Single Test Agent at Pos: ({spawn_x:.1f}, {spawn_y:.1f}) on Level {spawn_level + 1} with Gene({action_type}, dir={direction}, strength={strength:.1f})!")

    def stop_experiment(self) -> None:
        """
        Stops the experiment and despawns all agents.
        Displays the menu screen.
        """
        self.experiment_finished = True
        self.population.clear()
        self.test_agent = None
        self.menu_screen.show()

    def update(self) -> None:
        """
        Updates physics and input execution for all active agents and human player.
        Triggers GA generation evaluation and reproduction upon completion.

        Args:
            None

        Returns:
            None
        """
        if self.replay_engine.is_active:
            get_lvl = self.level_manager.get_level

            if self.replay_engine.active_agent:
                self.replay_engine.update(key.get_pressed(), get_lvl)
                
                if self.replay_engine.active_agent:
                    self.level_manager.current_level_index = self.replay_engine.active_agent.current_level_no
                    self.current_level = self.level_manager.get_current_level()
                    
            self.check_level_transitions()
            return

        if self.menu_screen.is_active or self.stats_screen.is_active or self.replay_screen.is_active or self.experiment_finished:
            self.check_level_transitions()
            return

        keys = key.get_pressed()
        get_lvl = self.level_manager.get_level
        
        cp = self.checkpoint_manager
        pm = self.pop_manager
        pop = self.population
        human = self.human_player
        test_agent = self.test_agent

        if human is not None and human.is_alive:
            env_level = get_lvl(human.current_level_no)
            human.handle_input(keys)
            human.update(env_level)
            if human.reached_princess:
                just_reached = RunRecorder.get_instance().record_princess_reached(
                    human,
                    pm.generation_number,
                    spawn_x=cp.spawn_x,
                    spawn_y=cp.spawn_y,
                    time_taken=0.0,
                    spawn_blizzard_force=cp.spawn_blizzard_force,
                    spawn_blizzard_force_dir=cp.spawn_blizzard_force_dir,
                    spawn_blizzard_timer=cp.spawn_blizzard_timer,
                    spawn_snow_pos=cp.spawn_snow_pos
                )
                if just_reached:
                    RunRecorder.get_instance().prompt_and_save(self)
                self.stop_experiment()

        if test_agent is not None:
            if not test_agent.is_alive:
                if not self.test_agent_reported_landing:
                    self.test_agent_reported_landing = True
            else:
                env_level = get_lvl(test_agent.current_level_no)
                test_agent.handle_input(None)
                test_agent.update(env_level)

                # landing position after action finishes
                if not self.test_agent_reported_landing:
                    controller = getattr(test_agent, "controller", None)
                    total_genes = len(controller.genome.genes) if (controller and hasattr(controller, "genome")) else 1
                    curr_g_idx = getattr(controller, "gene_index", 0) if controller else 0
                    is_jumping_active = (
                        getattr(test_agent, "jump_held", False) or
                        (getattr(test_agent, "jump_timer", 0) > 0) or
                        (not test_agent.is_on_ground) or
                        test_agent.is_sliding
                    )
                    is_grounded = bool(test_agent.is_on_ground and not test_agent.is_sliding and not is_jumping_active)

                    if curr_g_idx >= total_genes and is_grounded:
                        self.test_agent_reported_landing = True

                if test_agent.reached_princess:
                    just_reached = RunRecorder.get_instance().record_princess_reached(
                        test_agent,
                        pm.generation_number,
                        spawn_x=getattr(test_agent, "spawn_x", cp.spawn_x),
                        spawn_y=getattr(test_agent, "spawn_y", cp.spawn_y),
                        time_taken=0.0,
                        spawn_blizzard_force=cp.spawn_blizzard_force,
                        spawn_blizzard_force_dir=cp.spawn_blizzard_force_dir,
                        spawn_blizzard_timer=cp.spawn_blizzard_timer,
                        spawn_snow_pos=cp.spawn_snow_pos
                    )
                    if just_reached:
                        RunRecorder.get_instance().prompt_and_save(self)
                    self.stop_experiment()

        # update population agents 
        if not self.experiment_finished and pop:
            pm.generation_frames += 1

        for agent in pop:
            if agent.is_alive:
                env_level = get_lvl(agent.current_level_no)
                agent.handle_input(None)
                agent.update(env_level)
                if cp.update_checkpoint(agent, env_level, pm.generation_number, pm.generation_frames):
                    break
                if agent.reached_princess:
                    just_reached = RunRecorder.get_instance().record_princess_reached(
                        agent,
                        pm.generation_number,
                        spawn_x=cp.spawn_x,
                        spawn_y=cp.spawn_y,
                        time_taken=pm.generation_frames / Settings.FPS,
                        spawn_blizzard_force=cp.spawn_blizzard_force,
                        spawn_blizzard_force_dir=cp.spawn_blizzard_force_dir,
                        spawn_blizzard_timer=cp.spawn_blizzard_timer,
                        spawn_snow_pos=cp.spawn_snow_pos
                    )
                    if just_reached:
                        RunRecorder.get_instance().prompt_and_save(self)
                    self.stop_experiment()
                    break

        if not self.experiment_finished and pop and pm.is_generation_finished(pop, cp):
            next_genomes = pm.evaluate_and_evolve(pop, cp)
            # determine spawn origin for new gen
            if human is not None and human.is_alive:
                spawn_x = human.current_pos.x
                spawn_y = human.current_pos.y
                spawn_level = human.current_level_no
                b_force = human.blizzard_force
                b_dir = human.blizzard_force_dir
                b_timer = human.blizzard_timer
                b_snow = human.snow_pos
            else:
                spawn_x = cp.spawn_x
                spawn_y = cp.spawn_y
                spawn_level = cp.spawn_level
                b_force = cp.spawn_blizzard_force
                b_dir = cp.spawn_blizzard_force_dir
                b_timer = cp.spawn_blizzard_timer
                b_snow = cp.spawn_snow_pos

            for agent, genome in zip(pop, next_genomes):
                agent.controller = AgentController(genome)
                agent.reset(
                    spawn_x,
                    spawn_y,
                    level_no=spawn_level,
                    blizzard_force=b_force,
                    blizzard_force_dir=b_dir,
                    blizzard_timer=b_timer,
                    snow_pos=b_snow,
                )

            stag_str = ""
            if Settings.GA_MUTATION_STRATEGY == "REGRESSIVE":
                is_cooled = pm.current_mutation_rate_strength <= (Settings.GA_MUTATION_RATE_STRENGTH + Settings.GA_MUTATION_EPSILON)
                if is_cooled:
                    stag_str = f" | Stagnation: {pm.stagnation_counter}/{Settings.GA_PROGRESSIVE_STAGNATION_THRESHOLD}"
            else:
                is_maxed = pm.current_mutation_rate_strength >= (Settings.GA_REGRESSIVE_START_STRENGTH - Settings.GA_MUTATION_EPSILON)
                if is_maxed:
                    stag_str = f" | Stagnation: {pm.stagnation_counter}/{Settings.GA_PROGRESSIVE_STAGNATION_THRESHOLD}"
                else:
                    stag_str = f" | Stagnation: {pm.stagnation_counter}/{Settings.GA_STAGNATION_THRESHOLD}"

            print(f"Generation {pm.generation_number} started | Best Global Fit: {pm.best_global_fitness:.1f}{stag_str}")

        self.check_level_transitions()

    def check_level_transitions(self) -> None:
        """
        Synchronizes the camera view.

        Args:
            None

        Returns:
            None
        """
        if self.replay_engine.is_active and self.replay_engine.active_agent is not None:
            target_level = self.replay_engine.active_agent.current_level_no
        elif self.human_player is not None and self.human_player.is_alive:
            target_level = self.human_player.current_level_no
        elif self.test_agent is not None and self.test_agent.is_alive:
            target_level = self.test_agent.current_level_no
        else:
            active_levels = [a.current_level_no for a in self.population if a.is_alive]
            target_level = max(active_levels) if active_levels else self.level_manager.current_level_index

        if target_level != self.level_manager.current_level_index:
            self.level_manager.current_level_index = target_level
            self.current_level = self.level_manager.get_level(target_level)

    def draw(self) -> None:
        """
        Clears the screen and renders all active agents currently on the displayed level.

        Args:
            None

        Returns:
            None
        """
        self.screen.fill(Colors.BG_COLOR)

        self.current_level.draw(self.screen)

        curr_lvl_idx = self.level_manager.current_level_index

        if self.human_player is not None and self.human_player.is_alive and self.human_player.current_level_no == curr_lvl_idx:
            self.human_player.draw(self.screen)

        if self.replay_engine.is_active:
            self.replay_engine.draw(self.screen)
        else:
            if self.test_agent is not None and self.test_agent.is_alive and self.test_agent.current_level_no == curr_lvl_idx:
                self.test_agent.draw(self.screen)
    
            for agent in self.population:
                if agent.is_alive and agent.current_level_no == curr_lvl_idx:
                    agent.draw(self.screen)

        # render blizzard snow overlay
        if self.current_level.type == "snow" and self.snow_image is not None:
            width = Settings.WIDTH
            height = Settings.HEIGHT
            
            active_entity = self.human_player if (self.human_player and self.human_player.is_alive) else None
            if active_entity is None and self.replay_engine.is_active and self.replay_engine.active_agent:
                active_entity = self.replay_engine.active_agent
            if active_entity is None:
                for a in self.population:
                    if a.is_alive:
                        active_entity = a
                        break

            snow_draw_pos = active_entity.snow_pos if active_entity is not None else self.checkpoint_manager.spawn_snow_pos
            int_x = int(snow_draw_pos) % width

            if int_x == 0:
                self.screen.blit(self.snow_image, (0, 0))
            else:
                self.screen.blit(self.snow_image, (int_x, 0), Rect(0, 0, width - int_x, height))
                self.screen.blit(self.snow_image, (0, 0), Rect(width - int_x, 0, int_x, height))

        if self.menu_screen.is_active:
            self.menu_screen.draw(self.screen)

        if self.replay_screen.is_active:
            self.replay_screen.draw(self.screen)

        if self.stats_screen.is_active:
            self.stats_screen.draw(self.screen)

        display.flip()

    def run(self) -> None:
        """
        The main game loop. controls frame rate, window caption telemetry, and execution order.

        Args:
            None

        Returns:
            None
        """
        while self.running:
            self.handle_events()
            self.update()
            self.draw()

            self.frame_counter += 1
            if self.frame_counter % 15 == 0:
                if self.experiment_finished:
                    display.set_caption(
                        f"Jump King GA - EXPERIMENT FINISHED! Princess Reached"
                    )
                else:
                    pop = self.population
                    alive_count = sum(a.is_alive for a in pop)
                    
                    max_t = self.pop_manager.get_max_time_for_level(self.checkpoint_manager.spawn_level)
                    time_elapsed = self.pop_manager.generation_frames / Settings.FPS
                    time_l = max(0.0, max_t - time_elapsed)

                    current_gen_best = max((self.pop_manager.fitness_strategy.calculate_fitness(a, time_left=time_l, max_time=max_t) for a in pop), default=0.0)
                    overall_best = max(current_gen_best, self.pop_manager.best_global_fitness)
                    
                    time_left_str = ""
                    if Settings.GA_ACTIVE_SCENARIO == "SPEEDRUNNER":
                        time_left_str = f"Time Left: {time_l:.1f}s | "
                    
                    phase_str = "Phase 2" if Settings.GA_ALLOW_PROGRESSIVE_GROWTH else "Phase 1"
                    display.set_caption(
                        f"Jump King GA [{phase_str}] - Gen: {self.pop_manager.generation_number} | "
                        f"Alive: {alive_count}/{self.pop_manager.population_size} | "
                        f"Best Fit: {int(overall_best)} | "
                        f"Scenario: {Settings.GA_ACTIVE_SCENARIO} | "
                        f"{time_left_str}"
                        f"FPS: {int(self.clock.get_fps())}"
                    )

            self.clock.tick(Settings.FPS)