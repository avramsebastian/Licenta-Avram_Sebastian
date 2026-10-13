from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Union, Optional
from pygame import Vector2, Rect, key, K_LEFT, K_RIGHT, K_UP, K_DOWN, Surface, draw
from settings import Settings
from colors import Colors
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

@dataclass(slots=True)
class PlayerTelemetry:
    """
    Container for Genetic Algorithm fitness metrics and tracking.
    """
    collected_positive_coin_ids: set[str] = field(default_factory=set)
    collected_negative_coin_ids: set[str] = field(default_factory=set)
    coins_score_total: float = 0.0
    max_level_reached: int = 0
    max_height_reached: float = 0.0
    falls_count: int = 0
    fitness: float = 0.0
    reached_princess: bool = False

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
        self.reached_princess = False


class Player:
    """
    Represents the player entity.
    Maintains physical properties, state flags, input handling, rendering, and fitness telemetry.
    """

    __slots__ = (
        'width', 'height', 'current_pos', 'previous_pos', 'current_speed', 'previous_speed',
        'rect', 'controller', 'is_alive', 'is_on_ground', 'is_sliding', 'has_bumped',
        'fallen_timer', 'jump_timer', 'jump_held', 'jump_direction', 'facing_right',
        'hold_dir', 'current_level_no', 'spawn_level_no', 'jump_starting_height',
        'blizzard_force', 'blizzard_force_dir', 'blizzard_timer', 'snow_pos',
        'ignore_air_friction_frames', 'is_ghost', 'telemetry', 'reached_princess',
        'spawn_x', 'spawn_y'
    )

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
        # Spatial vectors & hitbox
        self.width: int = Settings.PLAYER_WIDTH
        self.height: int = Settings.PLAYER_HEIGHT
        self.current_pos: Vector2 = Vector2(x, y)
        self.previous_pos: Vector2 = Vector2(x, y)
        
        self.current_speed: Vector2 = Vector2()
        self.previous_speed: Vector2 = Vector2()
        self.rect: Rect = Rect(x, y, self.width, self.height)
        self.spawn_x: float = x
        self.spawn_y: float = y

        # input control
        self.controller: BaseController = controller if controller is not None else HumanController()
        self.is_alive: bool = True

        # Environment & physics flags
        self.is_on_ground: bool = True
        self.is_sliding: bool = False
        self.has_bumped: bool = False
        self.fallen_timer: int = 0  # Stun timer after a heavy fall

        # Jump & facing 
        self.jump_timer: int = 0
        self.jump_held: bool = False
        self.jump_direction: JumpDirection = JumpDirection.NONE
        self.facing_right: bool = True
        self.hold_dir: int = 0  # -1: LEFT, 0: NONE, 1: RIGHT

        # Environment & level state
        self.current_level_no: int = 0
        self.spawn_level_no: int = 0
        self.jump_starting_height: float = 0.0

        # Blizzard forces
        self.blizzard_force: float = 0.0
        self.blizzard_force_dir: int = Settings.BLIZZARD_INITIAL_DIRECTION
        self.blizzard_timer: int = 0
        self.snow_pos: float = 0.0
        self.ignore_air_friction_frames: int = 0

        self.is_ghost: bool = False # for debug

        # Telemetry
        self.telemetry: PlayerTelemetry = PlayerTelemetry(max_level_reached=self.current_level_no)
        self.reached_princess: bool = False 

    @property
    def coins_score_total(self) -> float:
        return self.telemetry.coins_score_total

    @coins_score_total.setter
    def coins_score_total(self, val: float) -> None:
        self.telemetry.coins_score_total = val

    @property
    def has_collected_level_coin(self) -> bool:
        return bool(self.telemetry.collected_positive_coin_ids)

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
        Returns True if the player is controlled by an agent controller.

        Args:
            None

        Returns:
            bool: True if controller is not a HumanController, False otherwise.
        """
        return type(self.controller) is not HumanController

    @property
    def current_height(self) -> float:
        """
        Calculates current vertical progress across levels heights.

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

    def reset(
        self,
        x: float,
        y: float,
        level_no: int = 0,
        blizzard_force: float = 0.0,
        blizzard_force_dir: int = Settings.BLIZZARD_INITIAL_DIRECTION,
        blizzard_timer: int = 0,
        snow_pos: float = 0.0,
    ) -> None:
        """
        Resets player state, telemetry, and environmental blizzard timestamp for a new generation.

        Args:
            x (float): Horizontal spawn position.
            y (float): Vertical spawn position.
            level_no (int): Spawn level index. Defaults to 0.
            blizzard_force (float): Active blizzard wind force at spawn checkpoint. Defaults to 0.0.
            blizzard_force_dir (int): Blizzard force acceleration direction (-1 or 1). Defaults to Settings.BLIZZARD_INITIAL_DIRECTION.
            blizzard_timer (int): Blizzard max force hold frames timer. Defaults to 0.
            snow_pos (float): Snow visual animation offset position. Defaults to 0.0.

        Returns:
            None
        """
        self.current_pos.update(x, y)
        self.previous_pos.update(x, y)
        self.spawn_x = x
        self.spawn_y = y
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
        self.reached_princess = False
        self.current_level_no = level_no
        self.spawn_level_no = level_no
        self.jump_starting_height = 0.0

        # Blizzard state
        self.blizzard_force = blizzard_force
        self.blizzard_force_dir = blizzard_force_dir
        self.blizzard_timer = blizzard_timer
        self.snow_pos = snow_pos

        self.telemetry.reset(start_level=level_no)
        self.controller.reset()

    # Input handling

    def handle_input(self, input_src: Optional[Union[key.ScancodeWrapper, PlayerInput]] = None) -> None:
        """
        Processes control inputs via the assigned controller.

        Args:
            input_src (Optional[Union[key.ScancodeWrapper, PlayerInput]]): Control input source.

        Returns:
            None
        """
        if not self.is_alive:
            return

        if type(input_src) is PlayerInput:
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
            if self.is_on_ground and not self.is_sliding:
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
        if type(input_src) is PlayerInput:
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

        self.jump_timer = 0
        self.jump_starting_height = self.current_height

    # Frame update & physics

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
        
        self.rect.topleft = self.current_pos
        
        self.check_coin_collisions(current_level)
        self.check_for_level_change()
        
        if self.current_level_no > self.telemetry.max_level_reached:
            self.telemetry.max_level_reached = self.current_level_no

    def check_coin_collisions(self, current_level: Any) -> None:
        """
        Checks for collision with level coins when the player is on solid ground.

        Args:
            current_level (Any): Current active Level object.

        Returns:
            None
        """
        telemetry = self.telemetry
        rect = self.rect
        
        if getattr(current_level, "is_last_level", False) or self.current_level_no >= Settings.MAX_LEVEL_INDEX:
            princess_coin = getattr(current_level, "princess_coin", None)
            if princess_coin is not None and not self.reached_princess and rect.colliderect(princess_coin.rect):
                self.reached_princess = True
                telemetry.reached_princess = True
                telemetry.coins_score_total += princess_coin.value

        if not self.is_on_ground:
            return

        coins = getattr(current_level, "coins", None)
        if not coins:
            return

        pos_coins = telemetry.collected_positive_coin_ids
        neg_coins = telemetry.collected_negative_coin_ids
        score = telemetry.coins_score_total

        for coin in coins:
            if getattr(coin, "is_princess", False):
                continue
                
            coin_id = coin.id
            if coin.is_negative:
                if coin_id not in neg_coins and rect.colliderect(coin.rect):
                    neg_coins.add(coin_id)
                    score += coin.value
            else:
                if coin_id not in pos_coins and rect.colliderect(coin.rect):
                    pos_coins.add(coin_id)
                    score += coin.value
                    
        telemetry.coins_score_total = score

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

        telemetry = self.telemetry
        fall_distance = self.jump_starting_height - self.current_height
        
        if fall_distance > Settings.MAX_FALL_DISTANCE:
            self.fallen_timer = Settings.FALLEN_STUN_TIME
            telemetry.falls_count += 1
        else:
            self.fallen_timer = 0

        if self.is_on_ground and not self.is_sliding and not self.is_stunned:
            if self.current_height > telemetry.max_height_reached:
                telemetry.max_height_reached = self.current_height

    def check_for_level_change(self) -> None:
        """
        Checks vertical screen transitions for moving up or falling down between levels.

        Args:
            None

        Returns:
            None
        """
        pos = self.current_pos
        
        if pos.y < -self.height:
            if self.current_level_no < Settings.MAX_LEVEL_INDEX:
                self.current_level_no += 1
                pos.y += Settings.HEIGHT
            else:
                pos.y = 0.0
                self.current_speed.y = 0.0
        elif pos.y > Settings.HEIGHT - self.height:
            if type(self.controller) is not HumanController:  
                if self.current_level_no > self.spawn_level_no:
                    self.current_level_no -= 1
                    pos.y -= Settings.HEIGHT
                else:
                    self.is_alive = False
            else:
                if self.current_level_no > 0:
                    self.current_level_no -= 1
                    pos.y -= Settings.HEIGHT
                else:
                    pos.y = Settings.HEIGHT - self.height
                    self.is_on_ground = True
                    self.current_speed.y = 0

    def update_telemetry(self) -> None:
        """
        Updates progression metrics.

        Args:
            None

        Returns:
            None
        """
        if self.current_level_no > self.telemetry.max_level_reached:
            self.telemetry.max_level_reached = self.current_level_no

    # Rendering state 

    def get_current_image_state(self) -> str:
        """
        Determines current active animation sprite state key.

        Args:
            None

        Returns:
            str: Sprite animation key string.
        """
        if self.is_stunned:
            return "fallen"
        elif self.has_bumped:
            return "oof"
        elif not self.is_on_ground:
            return "jump" if self.current_speed.y < 0 else "fall"
        else:
            if self.jump_held:
                return "squat"
            elif abs(self.current_speed.x) > 0.5 and not self.is_sliding:
                frame = (int(abs(self.current_pos.x) / 15) % 3) + 1
                return f"run{frame}"
            else:
                return "idle"

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
            draw.rect(surface, Colors.PLAYER_COLOR, self.rect)
            return

        offset_x = (self.width - img.get_width()) / 2
        offset_y = self.height - img.get_height()
        surface.blit(img, (self.current_pos.x + offset_x, self.current_pos.y + offset_y))