from typing import List, Optional, Dict
from random import uniform
from pygame import Surface, Clock, display, event as pygame_event, KEYDOWN, QUIT, K_r, K_t, K_p, K_o, key

from settings import Settings
from assets import AssetsManager
from player import Player
from environment import LevelManager, Level
from input_controllers import HumanController, AgentController
from ga_models import Genome, Gene, JUMP_BOUNDS
from ga_checkpoint import CheckpointManager
from ga_population import PopulationManager

class Game:
    """
    The main Engine class that handles the window, event polling,
    the core game loop, collision detection, rendering, level transitions,
    and automated Genetic Algorithm generation lifecycle.
    """

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

        # Preload graphics & assets
        AssetsManager.get_instance().load_assets()

        self.level_manager: LevelManager = LevelManager(Settings.LEVEL_DATA_PATH)
        self.current_level: Level = self.level_manager.get_current_level()

        # Checkpoint Manager for Population Spawning
        self.checkpoint_manager: CheckpointManager = CheckpointManager(Settings.START_X, Settings.START_Y, 0)

        # Population Manager for Genetic Algorithm Evolutionary Lifecycle
        self.pop_manager: PopulationManager = PopulationManager()

        # Optional Human Test Player (by pressing the 'T' key)
        self.human_player: Optional[Player] = None

        # Single Test AI Agent for experiment testing (by pressing the 'O' key)
        self.test_agent: Optional[Player] = None

        # Spawn Population of AI Agents from Settings
        self.population: List[Player] = []
        for _ in range(self.pop_manager.population_size):
            controller = AgentController(Genome.random_genome(length=Settings.GA_GENOME_LENGTH))
            agent = Player(Settings.START_X, Settings.START_Y, controller=controller)
            agent.current_level_no = self.level_manager.current_level_index
            self.population.append(agent)

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
        for event in pygame_event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == KEYDOWN:
                if event.key == K_r:
                    self.pop_manager.reset_evolution()

                    if self.human_player is not None and self.human_player.is_alive:
                        spawn_x = self.human_player.current_pos.x
                        spawn_y = self.human_player.current_pos.y
                        spawn_level = self.human_player.current_level_no
                        loc_str = f"Human Player Position (Level {spawn_level + 1})"
                    else:
                        spawn_x = self.checkpoint_manager.spawn_x
                        spawn_y = self.checkpoint_manager.spawn_y
                        spawn_level = self.checkpoint_manager.spawn_level
                        loc_str = f"Checkpoint (Level {spawn_level + 1})"
                    
                    for agent in self.population:
                        agent.controller = AgentController(Genome.random_genome(length=Settings.GA_GENOME_LENGTH))
                        agent.reset(spawn_x, spawn_y, level_no=spawn_level)

                    print(f"Reset Agents!")
                elif event.key == K_t:
                    if self.human_player is None:
                        spawn_x = self.checkpoint_manager.spawn_x
                        spawn_y = self.checkpoint_manager.spawn_y
                        spawn_level = self.checkpoint_manager.spawn_level
                        self.human_player = Player(spawn_x, spawn_y, controller=HumanController())
                        self.human_player.current_level_no = spawn_level
                        print(f"Spawned Test Player at Level {spawn_level + 1}!")
                    else:
                        self.human_player = None
                        print("Despawned Test Player!")
                elif event.key == K_p:
                    self.population.clear()
                    self.test_agent = None
                    print("Despawned all agents!")
                elif event.key == K_o:
                    if self.test_agent is not None:
                        self.test_agent = None
                        print("Despawned Single Test Agent!")
                    else:
                        print("Single test agent configuration!")
                        try:
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

                        if self.human_player is not None and self.human_player.is_alive:
                            spawn_x = self.human_player.current_pos.x
                            spawn_y = self.human_player.current_pos.y
                            spawn_level = self.human_player.current_level_no
                            loc_str = f"Player position (Level {spawn_level + 1})"
                        else:
                            spawn_x = self.checkpoint_manager.spawn_x
                            spawn_y = self.checkpoint_manager.spawn_y
                            spawn_level = self.checkpoint_manager.spawn_level
                            loc_str = f"Checkpoint Level {spawn_level + 1}"

                        test_gene = Gene(action_type=action_type, direction=direction, strength=strength)
                        test_genome = Genome(genes=[test_gene])
                        self.test_agent = Player(spawn_x, spawn_y, controller=AgentController(test_genome))
                        self.test_agent.current_level_no = spawn_level
                        print(f"Spawned Single Test Agent at {loc_str} with Gene({action_type}, dir={direction}, strength={strength:.1f})!")

    def update(self) -> None:
        """
        Updates physics and input execution for all active agents and human player.
        Uses local level caching to eliminate redundant LevelManager dictionary lookups per frame.
        Triggers GA generation evaluation and reproduction upon completion.

        Args:
            None

        Returns:
            None
        """
        keys = key.get_pressed()
        active_levels: Dict[int, Level] = {}

        if self.human_player is not None and self.human_player.is_alive:
            lvl_no = self.human_player.current_level_no
            if lvl_no not in active_levels:
                active_levels[lvl_no] = self.level_manager.get_level(lvl_no)
            self.human_player.handle_input(keys)
            self.human_player.update(active_levels[lvl_no])

        if self.test_agent is not None and self.test_agent.is_alive:
            lvl_no = self.test_agent.current_level_no
            if lvl_no not in active_levels:
                active_levels[lvl_no] = self.level_manager.get_level(lvl_no)
            self.test_agent.handle_input(None)
            self.test_agent.update(active_levels[lvl_no])

        # Update AI Population Agents
        for agent in self.population:
            if agent.is_alive:
                lvl_no = agent.current_level_no
                if lvl_no not in active_levels:
                    active_levels[lvl_no] = self.level_manager.get_level(lvl_no)
                env_level = active_levels[lvl_no]
                agent.handle_input(None)
                agent.update(env_level)
                self.checkpoint_manager.update_checkpoint(agent, env_level)

        if self.population and self.pop_manager.is_generation_finished(self.population, self.checkpoint_manager):
            next_genomes = self.pop_manager.evaluate_and_evolve(self.population, self.checkpoint_manager)

            # Determine Spawn Origin for New Generation
            if self.human_player is not None and self.human_player.is_alive:
                spawn_x = self.human_player.current_pos.x
                spawn_y = self.human_player.current_pos.y
                spawn_level = self.human_player.current_level_no
            else:
                spawn_x = self.checkpoint_manager.spawn_x
                spawn_y = self.checkpoint_manager.spawn_y
                spawn_level = self.checkpoint_manager.spawn_level

            # Re-assign evolved genomes & reset population
            for agent, genome in zip(self.population, next_genomes):
                agent.controller = AgentController(genome)
                agent.reset(spawn_x, spawn_y, level_no=spawn_level)

            print(f"Generation {self.pop_manager.generation_number} started | Best Global Fit: {self.pop_manager.best_global_fitness:.1f} | Stagnation: {self.pop_manager.stagnation_counter}/{Settings.GA_STAGNATION_THRESHOLD}")

        self.check_level_transitions()

    def check_level_transitions(self) -> None:
        """
        Synchronizes the camera view with the human test player if present, single test agent, or the lead active AI agent.

        Args:
            None

        Returns:
            None
        """
        if self.human_player is not None and self.human_player.is_alive:
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
        Clears the screen and renders all active AI agents and Human Test Player currently on the displayed level.

        Args:
            None

        Returns:
            None
        """
        self.screen.fill(Settings.BG_COLOR)

        self.current_level.draw(self.screen)

        if self.human_player is not None and self.human_player.is_alive and self.human_player.current_level_no == self.level_manager.current_level_index:
            self.human_player.draw(self.screen)

        if self.test_agent is not None and self.test_agent.is_alive and self.test_agent.current_level_no == self.level_manager.current_level_index:
            self.test_agent.draw(self.screen)

        for agent in self.population:
            if agent.is_alive and agent.current_level_no == self.level_manager.current_level_index:
                agent.draw(self.screen)

        # Render Blizzard snow overlay if applicable
        snow = AssetsManager.get_instance().get_snow_image()
        if self.current_level.is_blizzard_level and snow is not None:
            width = Settings.WIDTH
            
            active_entity = self.human_player if (self.human_player and self.human_player.is_alive) else None
            if active_entity is None:
                alive_agents = [a for a in self.population if a.is_alive]
                active_entity = alive_agents[0] if alive_agents else None

            snow_draw_pos = active_entity.snow_pos if active_entity is not None else 0.0

            while snow_draw_pos <= 0:
                snow_draw_pos += width
            snow_draw_pos = snow_draw_pos % width

            self.screen.blit(snow, (snow_draw_pos, 0))
            self.screen.blit(snow, (snow_draw_pos - width, 0))

        display.flip()

    def run(self) -> None:
        """
        The main game loop. Controls frame rate, window caption telemetry, and execution order.

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
                alive_count = sum(1 for a in self.population if a.is_alive)
                current_gen_best = max((self.pop_manager.fitness_strategy.calculate_fitness(a, time_left=0.0, max_time=0.0) for a in self.population), default=0.0)
                overall_best = max(current_gen_best, self.pop_manager.best_global_fitness)
                display.set_caption(
                    f"Jump King GA - Gen: {self.pop_manager.generation_number} | "
                    f"Alive: {alive_count}/{self.pop_manager.population_size} | "
                    f"Best Fit: {int(overall_best)} | "
                    f"Mut Direction/Strength: {self.pop_manager.current_mutation_rate_dir:.0%}/{self.pop_manager.current_mutation_rate_strength:.0%} | "
                    f"Scenario: {Settings.GA_ACTIVE_SCENARIO}| "
                    f"FPS: {int(self.clock.get_fps())}"
                )

            self.clock.tick(Settings.FPS)