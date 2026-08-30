from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Union, Optional
from pygame import Vector2, Rect, key, K_LEFT, K_RIGHT, K_UP, K_DOWN, Surface, draw

from settings import Settings
from assets import AssetsManager
from input_controllers import PlayerInput, BaseController, HumanController
from physics import PhysicsEngine

class JumpDirection(Enum):
    NONE = 0
    LEFT = -1
    RIGHT = 1

class PlayerState(Enum):
    IDLE = "idle"
    RUN = "run"
    SQUAT = "squat"
    JUMP = "jump"
    FALL = "fall"
    FALLEN = "fallen"
    OOF = "oof"

@dataclass
class PlayerTelemetry:
    """
    Container for Genetic Algorithm fitness metrics and tracking.
    Separates concerns between physical simulation and evolutionary evaluation telemetry.
    """
    collected_positive_coin_ids: set[str] = field(default_factory=set)
    collected_negative_coin_ids: set[str] = field(default_factory=set)
    coins_score_total: float = 0.0
    max_level_reached: int = 0
    max_height_reached: float = 0.0
    falls_count: int = 0
    fitness: float = 0.0

    def reset(self, start_level: int = 0) -> None:
        """
        Resets telemetry metrics for a new generation.

        Args:
            start_level (int): Spawn level index. Defaults to 0.

        Returns:
            None
        """
        self.collected_positive_coin_ids.clear()
        self.collected_negative_coin_ids.clear()
        self.coins_score_total = 0.0
        self.max_level_reached = start_level
        self.max_height_reached = 0.0
        self.falls_count = 0
        self.fitness = 0.0


class Player:
    """
    Represents the Jump King player entity.
    Maintains physical properties, state flags, input handling, rendering, 
    and fitness telemetry for Genetic Algorithm training.
    """

    def __init__(self, x: float, y: float, controller: Optional[BaseController]) -> None:
        """
        Initializes player entity properties, spatial vectors, and input controller.

        Args:
            x (float): Initial horizontal position coordinate.
            y (float): Initial vertical position coordinate.
            controller (Optional[BaseController]): Input controller instance.

        Returns:
            None
        """
        # Spatial Vectors & Hitbox
        self.width: int = Settings.PLAYER_WIDTH
        self.height: int = Settings.PLAYER_HEIGHT
        self.current_pos: Vector2 = Vector2(x, y)
        self.previous_pos: Vector2 = Vector2(x, y)
        self.current_speed: Vector2 = Vector2(0, 0)
        self.previous_speed: Vector2 = Vector2(0, 0)
        self.rect: Rect = Rect(x, y, self.width, self.height)

        # Strategy Pattern for injection of input control
        self.controller: BaseController = controller if controller is not None else HumanController()
        self.is_alive: bool = True

        # Environment & Physics State Flags
        self.is_on_ground: bool = True
        self.is_sliding: bool = False
        self.has_bumped: bool = False
        self.fallen_timer: int = 0  # Stun timer after a heavy fall

        # Jump & Facing Mechanics
        self.jump_timer: int = 0
        self.jump_held: bool = False
        self.jump_direction: JumpDirection = JumpDirection.NONE
        self.facing_right: bool = True
        self.hold_dir: int = 0  # -1: LEFT, 0: NONE, 1: RIGHT

        # Environment & Level State
        self.current_level_no: int = 0
        self.spawn_level_no: int = 0
        self.jump_starting_height: float = 0.0

        # Blizzard Forces
        self.blizzard_force: float = 0.0
        self.blizzard_force_dir: int = 1
        self.blizzard_timer: int = 0
        self.snow_pos: float = 0.0
        self.ignore_air_friction_frames: int = 0

        # Debug Flags
        self.is_ghost: bool = False

        # Genetic Algorithm Fitness Telemetry
        self.telemetry: PlayerTelemetry = PlayerTelemetry(max_level_reached=self.current_level_no)

    @property
    def coins_score_total(self) -> float:
        return self.telemetry.coins_score_total

    @coins_score_total.setter
    def coins_score_total(self, val: float) -> None:
        self.telemetry.coins_score_total = val

    @property
    def has_collected_level_coin(self) -> bool:
        return len(self.telemetry.collected_positive_coin_ids) > 0

    @property
    def max_level_reached(self) -> int:
        return self.telemetry.max_level_reached

    @max_level_reached.setter
    def max_level_reached(self, val: int) -> None:
        self.telemetry.max_level_reached = val

    @property
    def max_height_reached(self) -> float:
        return self.telemetry.max_height_reached

    @max_height_reached.setter
    def max_height_reached(self, val: float) -> None:
        self.telemetry.max_height_reached = val

    @property
    def falls_count(self) -> int:
        return self.telemetry.falls_count

    @falls_count.setter
    def falls_count(self, val: int) -> None:
        self.telemetry.falls_count = val

    @property
    def fitness(self) -> float:
        return self.telemetry.fitness

    @fitness.setter
    def fitness(self, val: float) -> None:
        self.telemetry.fitness = val

    @property
    def left_held(self) -> bool:
        """
        Returns True if left movement key is held.

        Args:
            None

        Returns:
            bool: True if hold_dir < 0, False otherwise.
        """
        return self.hold_dir < 0

    @property
    def right_held(self) -> bool:
        """
        Returns True if right movement key is held.

        Args:
            None

        Returns:
            bool: True if hold_dir > 0, False otherwise.
        """
        return self.hold_dir > 0

    @property
    def is_agent(self) -> bool:
        """
        Returns True if the player is controlled by an AI / Genetic controller.

        Args:
            None

        Returns:
            bool: True if controller is not a HumanController, False otherwise.
        """
        return not isinstance(self.controller, HumanController)

    @property
    def current_height(self) -> float:
        """
        Calculates current vertical progress across multi-level heights.

        Args:
            None

        Returns:
            float: Cumulative height score in pixels.
        """
        return (Settings.HEIGHT - self.current_pos.y) + (Settings.HEIGHT * self.current_level_no)

    @property
    def is_stunned(self) -> bool:
        """
        Returns True if player is recovering from a heavy fall.

        Args:
            None

        Returns:
            bool: True if fallen_timer > 0, False otherwise.
        """
        return self.fallen_timer > 0

    def set_fallen(self) -> None:
        """
        Sets player to fallen stun state.

        Args:
            None

        Returns:
            None
        """
        if self.fallen_timer <= 0:
            self.fallen_timer = Settings.FALLEN_STUN_TIME

    def reset(self, x: float, y: float, level_no: int = 0) -> None:
        """
        Resets player state and telemetry for a new GA generation episode.
        Uses vector update in-place for zero memory allocation overhead.

        Args:
            x (float): Horizontal spawn position.
            y (float): Vertical spawn position.
            level_no (int): Spawn level index. Defaults to 0.

        Returns:
            None
        """
        self.current_pos.update(x, y)
        self.previous_pos.update(x, y)
        self.current_speed.update(0, 0)
        self.previous_speed.update(0, 0)
        self.rect.topleft = (x, y)

        self.is_alive = True
        self.is_on_ground = True
        self.is_sliding = False
        self.has_bumped = False
        self.fallen_timer = 0
        self.jump_timer = 0
        self.jump_held = False
        self.jump_direction = JumpDirection.NONE
        self.facing_right = True
        self.hold_dir = 0
        self.current_level_no = level_no
        self.spawn_level_no = level_no
        self.jump_starting_height = 0.0

        self.telemetry.reset(start_level=level_no)
        self.controller.reset()

    # Input Handling

    def handle_input(self, input_src: Optional[Union[key.ScancodeWrapper, PlayerInput]] = None) -> None:
        """
        Processes control inputs via the assigned Controller strategy.

        Args:
            input_src (Optional[Union[key.ScancodeWrapper, PlayerInput]]): Control input source.

        Returns:
            None
        """
        if not self.is_alive:
            return

        if isinstance(input_src, PlayerInput):
            action = input_src
        else:
            action = self.controller.get_input(input_src or self)

        self.is_ghost = action.ghost
        if self.is_ghost:
            self._handle_ghost_movement(input_src)
            return

        if self.is_stunned:
            self.hold_dir = 0
            self.jump_held = False
            return

        if action.left:
            self.hold_dir = -1
        elif action.right:
            self.hold_dir = 1
        else:
            self.hold_dir = 0

        if not self.jump_held and self.is_on_ground:
            if self.hold_dir < 0:
                self.facing_right = False
            elif self.hold_dir > 0:
                self.facing_right = True

        if action.jump:
            if self.is_on_ground:
                if not self.jump_held:
                    self.jump_held = True
                    self.jump_timer = 0
                    self.jump_direction = JumpDirection.RIGHT if self.facing_right else JumpDirection.LEFT
                if self.hold_dir < 0:
                    self.jump_direction = JumpDirection.LEFT
                elif self.hold_dir > 0:
                    self.jump_direction = JumpDirection.RIGHT
        else:
            if self.jump_held:
                self.jump_held = False
                self.perform_jump()
                self.jump_direction = JumpDirection.NONE

    def _handle_ghost_movement(self, input_src: Any) -> None:
        """
        Processes debug ghost movement without physical collision checks.

        Args:
            input_src (Any): Input state reference.

        Returns:
            None
        """
        speed = Settings.GHOST_SPEED
        if isinstance(input_src, PlayerInput):
            if input_src.left: self.current_pos.x -= speed
            if input_src.right: self.current_pos.x += speed
        elif input_src is not None:
            keys = input_src
            if keys[K_LEFT]:  self.current_pos.x -= speed
            if keys[K_RIGHT]: self.current_pos.x += speed
            if keys[K_UP]:    self.current_pos.y -= speed
            if keys[K_DOWN]:  self.current_pos.y += speed
        self.current_speed.update(0, 0)
        self.check_for_level_change()

    def perform_jump(self) -> None:
        """
        Calculates jump velocities based on charge timer and launches player into the air.

        Args:
            None

        Returns:
            None
        """
        if not self.is_on_ground:
            return

        charge_ratio = self.jump_timer / Settings.MAX_JUMP_TIMER
        vertical_speed = Settings.MIN_JUMP_SPEED + charge_ratio * (Settings.MAX_JUMP_SPEED - Settings.MIN_JUMP_SPEED)
        horizontal_speed = self.jump_direction.value * Settings.JUMP_SPEED_HORIZONTAL

        self.current_speed.update(horizontal_speed, -vertical_speed)
        self.is_on_ground = False

        #print(f"Dir: {self.jump_direction.name} | Power Speed: {vertical_speed:.2f} | Charge: {charge_ratio:.1%} ({self.jump_timer}/{Settings.MAX_JUMP_TIMER} frames)")

        self.jump_timer = 0
        self.jump_starting_height = self.current_height

    # Frame Update & Physics Delegate

    def update(self, current_level: Any) -> None:
        """
        Delegates physics calculations and collision resolution to PhysicsEngine.

        Args:
            current_level (Any): Current active Level object.

        Returns:
            None
        """
        if not self.is_alive:
            return

        PhysicsEngine.update_entity_physics(self, current_level)
        self.rect.topleft = (self.current_pos.x, self.current_pos.y)
        self.check_coin_collisions(current_level)
        self.check_for_level_change()
        self.update_telemetry()

    def check_coin_collisions(self, current_level: Any) -> None:
        """
        Checks for collision with positive and negative level coins using set tracking.
        Coins can only be collected when the player is supported on solid ground (is_on_ground).

        Args:
            current_level (Any): Current active Level object.

        Returns:
            None
        """
        if not self.is_on_ground:
            return
            
        if not hasattr(current_level, "coins") or not current_level.coins:
            return
        self.rect.topleft = (self.current_pos.x, self.current_pos.y)
        for coin in current_level.coins:
            coin_id = getattr(coin, "id", f"coin_{int(coin.x)}_{int(coin.y)}")
            is_neg = getattr(coin, "is_negative", False) or getattr(coin, "value", 500.0) < 0

            if is_neg:
                if coin_id not in self.telemetry.collected_negative_coin_ids and self.rect.colliderect(coin.rect):
                    self.telemetry.collected_negative_coin_ids.add(coin_id)
                    val = getattr(coin, "value", -300.0)
                    self.telemetry.coins_score_total += val
            else:
                if coin_id not in self.telemetry.collected_positive_coin_ids and self.rect.colliderect(coin.rect):
                    self.telemetry.collected_positive_coin_ids.add(coin_id)
                    val = getattr(coin, "value", 500.0)
                    self.telemetry.coins_score_total += val

    def player_landed(self) -> None:
        """
        Triggered upon solid ground landing. Resets grounding state and calculates fall stun distance.

        Args:
            None

        Returns:
            None
        """
        self.is_on_ground = True
        self.current_speed.y = 0
        self.has_bumped = False

        fall_distance = self.jump_starting_height - self.current_height
        if fall_distance > Settings.MAX_FALL_DISTANCE:
            self.fallen_timer = Settings.FALLEN_STUN_TIME
            self.telemetry.falls_count += 1
        else:
            self.fallen_timer = 0

        if self.is_on_ground and not self.is_sliding and not self.is_stunned:
            if self.current_height > self.telemetry.max_height_reached:
                self.telemetry.max_height_reached = self.current_height

    def check_for_level_change(self) -> None:
        """
        Checks vertical screen transitions for moving up or falling down between levels.
        Prevents advancing beyond Settings.MAX_LEVEL_INDEX to avoid teleportation loops.

        Args:
            None

        Returns:
            None
        """
        if self.current_pos.y < -self.height:
            if self.current_level_no < Settings.MAX_LEVEL_INDEX:
                self.current_level_no += 1
                self.current_pos.y += Settings.HEIGHT
            else:
                self.current_pos.y = 0.0
                self.current_speed.y = 0.0
        elif self.current_pos.y > Settings.HEIGHT - self.height:
            if self.is_agent:
                if self.current_level_no > self.spawn_level_no:
                    self.current_level_no -= 1
                    self.current_pos.y -= Settings.HEIGHT
                else:
                    self.is_alive = False
            else:
                if self.current_level_no > 0:
                    self.current_level_no -= 1
                    self.current_pos.y -= Settings.HEIGHT
                else:
                    self.current_pos.y = Settings.HEIGHT - self.height
                    self.is_on_ground = True
                    self.current_speed.y = 0

    def update_telemetry(self) -> None:
        """
        Updates peak progression metrics.

        Args:
            None

        Returns:
            None
        """
        if self.current_level_no > self.telemetry.max_level_reached:
            self.telemetry.max_level_reached = self.current_level_no

    # Rendering State 

    def get_current_image_state(self) -> str:
        """
        Determines current active animation sprite state key.

        Args:
            None

        Returns:
            str: Sprite animation key string.
        """
        if self.is_stunned:
            return PlayerState.FALLEN.value
        elif self.has_bumped:
            return PlayerState.OOF.value
        elif not self.is_on_ground:
            return PlayerState.JUMP.value if self.current_speed.y < 0 else PlayerState.FALL.value
        else:
            if self.jump_held:
                return PlayerState.SQUAT.value
            elif abs(self.current_speed.x) > 0.5 and not self.is_sliding:
                frame = (int(abs(self.current_pos.x) / 15) % 3) + 1
                return f"run{frame}"
            else:
                return PlayerState.IDLE.value

    def draw(self, surface: Surface) -> None:
        """
        Renders the player using the AssetsManager.

        Args:
            surface (Surface): Rendering surface.

        Returns:
            None
        """
        if not self.is_alive:
            return

        state = self.get_current_image_state()
        img = AssetsManager.get_instance().get_player_sprite(state, self.facing_right)

        if img is None:
            draw.rect(surface, Settings.PLAYER_COLOR, self.rect)
            return

        offset_x = (self.width - img.get_width()) / 2
        offset_y = self.height - img.get_height()
        surface.blit(img, (self.current_pos.x + offset_x, self.current_pos.y + offset_y))