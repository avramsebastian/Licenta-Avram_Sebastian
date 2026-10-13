from __future__ import annotations
from dataclasses import dataclass, field
from json import load
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pygame import Rect, Surface, draw
from assets import AssetsManager
from geometry import Direction, Line, LineType
from settings import Settings
from colors import Colors


@dataclass(slots=True)
class Platform:
    """
    Represents a physical platform in the game world that entities can stand on or collide with.
    """
    x: int
    y: int
    width: int
    height: int
    friction: float = Settings.NORMAL_FRICTION
    wind_push: float = Settings.NORMAL_WIND_PUSH
    platform_type: str = "normal"
    rect: Rect = field(init=False)

    def __post_init__(self) -> None:
        """
        Constructs the bounding Rect after dataclass initialization.

        Args:
            None

        Returns:
            None
        """
        self.rect = Rect(self.x, self.y, self.width, self.height)

    def draw(self, surface: Surface) -> None:
        """
        Renders the platform outline on the target surface.

        Args:
            surface (Surface): Target surface to render onto.

        Returns:
            None
        """
        draw.rect(surface, Colors.PLATFORM_COLOR, self.rect, 3)

    @property
    def is_horizontal(self) -> bool:
        """
        Returns True if platform width is greater than its height.

        Args:
            None

        Returns:
            bool: True if horizontal floor, False otherwise.
        """
        return self.rect.width > self.rect.height

    @property
    def is_vertical(self) -> bool:
        """
        Returns True if platform height is greater than its width.

        Args:
            None

        Returns:
            bool: True if vertical wall, False otherwise.
        """
        return self.rect.height > self.rect.width


@dataclass(slots=True)
class Ramp:
    """
    Represents a diagonal surface in the game, defined by two points (x1, y1) and (x2, y2).
    """
    x1: int
    y1: int
    x2: int
    y2: int
    friction: float = Settings.NORMAL_FRICTION
    wind_push: float = Settings.NORMAL_WIND_PUSH
    ramp_type: str = "normal"
    _slope: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """
        Ensures (x1, y1) is always the left-most point and pre-calculates the slope.

        Args:
            None

        Returns:
            None
        """
        if self.x1 > self.x2:
            self.x1, self.x2 = self.x2, self.x1
            self.y1, self.y2 = self.y2, self.y1
            
        self._slope = (self.y2 - self.y1) / (self.x2 - self.x1) if self.x2 != self.x1 else 0.0

    def get_y_at_x(self, player_x: float) -> Optional[float]:
        """
        Calculates vertical Y coordinate along the ramp segment for a given X coordinate.

        Args:
            player_x (float): Horizontal position along the X-axis.

        Returns:
            Optional[float]: Calculated Y coordinate if within ramp bounds, None otherwise.
        """
        if self.x1 <= player_x <= self.x2:
            return self.y1 + (player_x - self.x1) * self._slope
        return None

    def draw(self, surface: Surface) -> None:
        """
        Renders the ramp line segment on the target surface.

        Args:
            surface (Surface): Target surface to render onto.

        Returns:
            None
        """
        draw.line(surface, Colors.PLATFORM_COLOR, (self.x1, self.y1), (self.x2, self.y2), 4)


@dataclass(slots=True)
class Coin:
    """
    Collectible coin for reward shaping (positive, negative and princess coins).
    """
    x: float
    y: float
    radius: float = Settings.COIN_RADIUS
    value: float = Settings.GA_COIN_REWARD_VALUE
    is_negative: bool = False
    is_princess: bool = False
    id: str = ""
    rect: Rect = field(init=False)
    
    # Pre calculated rendering fields to avoid frame drops
    _render_pos: Tuple[int, int] = field(init=False, repr=False)
    _render_radius: int = field(init=False, repr=False)
    _color: Tuple[int, int, int] = field(init=False, repr=False)
    _p_shine_pos: Tuple[int, int] = field(init=False, repr=False)
    _p_shine_radius: int = field(init=False, repr=False)
    _p_outer_radius: int = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """
        Constructs the bounding Rect after dataclass initialization.
        Assigns default value, unique identifier, and pre-calculates rendering data.

        Args:
            None

        Returns:
            None
        """
        if self.is_princess:
            if self.value == Settings.GA_COIN_REWARD_VALUE:
                self.value = Settings.GA_PRINCESS_REWARD_VALUE
            if not self.id:
                self.id = f"princess_{int(self.x)}_{int(self.y)}"
        elif self.is_negative and self.value == Settings.GA_COIN_REWARD_VALUE:
            self.value = Settings.GA_COIN_PENALTY_VALUE
            if not self.id:
                self.id = f"coin_neg_{int(self.x)}_{int(self.y)}"
        elif not self.id:
            self.id = f"coin_{int(self.x)}_{int(self.y)}"
            
        self.rect = Rect(self.x - self.radius, self.y - self.radius, self.radius * 2, self.radius * 2)

        # Pre compute rendering mathematics
        self._render_pos = (int(self.x), int(self.y))
        self._render_radius = int(self.radius)
        
        if self.is_princess:
            self._p_outer_radius = int(self.radius + 2)
            self._p_shine_pos = (int(self.x - self.radius * 0.3), int(self.y - self.radius * 0.3))
            self._p_shine_radius = int(self.radius * 0.25)
            self._color = Colors.PRINCESS_COIN_COLOR  # Placeholder for static typing
        else:
            self._p_outer_radius = 0
            self._p_shine_pos = (0, 0)
            self._p_shine_radius = 0
            self._color = Colors.NEGATIVE_COIN_COLOR if (self.is_negative or self.value < 0) else Colors.COIN_COLOR

    def draw(self, surface: Surface) -> None:
        """
        Renders coins with their colors.

        Args:
            surface (Surface): Target surface to render onto.

        Returns:
            None
        """
        if self.is_princess:
            draw.circle(surface, Colors.PRINCESS_RIM_COLOR, self._render_pos, self._p_outer_radius)
            draw.circle(surface, Colors.PRINCESS_COIN_COLOR, self._render_pos, self._render_radius)
            draw.circle(surface, Colors.PRINCESS_SHINE_COLOR, self._p_shine_pos, self._p_shine_radius)
        else:
            draw.circle(surface, self._color, self._render_pos, self._render_radius)

class PlatformFactory:
    """
    Decouples platform, ramp, and coin creation from dictionary data.
    """
    __slots__ = ()

    @staticmethod
    def create_platform(data: Dict[str, Any]) -> Platform:
        """
        Creates a Platform instance with dictionary data.

        Args:
            data (Dict[str, Any]): Dictionary containing platform fields (x, y, width, height, type, etc.).

        Returns:
            Platform: Instantiated Platform object.
        """
        p_type: str = data.get("type", "normal")
        if p_type == "snow":
            friction = Settings.NORMAL_FRICTION
            wind_push = Settings.SNOW_WIND_PUSH
        elif p_type == "ice":
            friction = Settings.ICE_FRICTION
            wind_push = Settings.NORMAL_WIND_PUSH
        else:
            friction = Settings.NORMAL_FRICTION
            wind_push = Settings.NORMAL_WIND_PUSH

        return Platform(
            x=data["x"],
            y=data["y"],
            width=data["width"],
            height=data["height"],
            friction=friction,
            wind_push=wind_push,
            platform_type=p_type
        )

    @staticmethod
    def create_ramp(data: Dict[str, Any]) -> Ramp:
        """
        Creates a Ramp instance with dictionary data.

        Args:
            data (Dict[str, Any]): Dictionary containing ramp fields (x1, y1, x2, y2, type, etc.).

        Returns:
            Ramp: Instantiated Ramp object.
        """
        r_type: str = data.get("type", "normal")
        if r_type == "snow":
            friction = Settings.NORMAL_FRICTION
            wind_push = Settings.SNOW_WIND_PUSH
        elif r_type == "ice":
            friction = Settings.ICE_FRICTION
            wind_push = Settings.NORMAL_WIND_PUSH
        else:
            friction = Settings.NORMAL_FRICTION
            wind_push = Settings.NORMAL_WIND_PUSH

        return Ramp(
            x1=data["x1"],
            y1=data["y1"],
            x2=data["x2"],
            y2=data["y2"],
            friction=friction,
            wind_push=wind_push,
            ramp_type=r_type
        )

    @staticmethod
    def create_coin(data: Dict[str, Any], level_index: int = 0, coin_index: int = 0) -> Coin:
        """
        Creates a Coin instance with dictionary data.

        Args:
            data (Dict[str, Any]): Dictionary containing coin fields (x, y, radius, value, is_negative, is_princess, id).
            level_index (int): Index of the parent level for default ID generation.
            coin_index (int): Index of the coin in the level for default ID generation.

        Returns:
            Coin: Instantiated Coin object.
        """
        is_princess = data.get("is_princess", False)
        is_neg = data.get("is_negative", False)

        if is_princess:
            default_val = Settings.GA_PRINCESS_REWARD_VALUE
            default_radius = Settings.PRINCESS_COIN_RADIUS
            coin_id = data.get("id", f"princess_l{level_index}_{coin_index}_{int(data['x'])}_{int(data['y'])}")
        else:
            default_val = Settings.GA_COIN_PENALTY_VALUE if is_neg else Settings.GA_COIN_REWARD_VALUE
            default_radius = Settings.COIN_RADIUS
            coin_id = data.get("id", f"coin_l{level_index}_{coin_index}_{int(data['x'])}_{int(data['y'])}")

        val = data.get("value", default_val)
        radius = data.get("radius", default_radius)

        return Coin(
            x=data["x"],
            y=data["y"],
            radius=radius,
            value=val,
            is_negative=is_neg,
            is_princess=is_princess,
            id=coin_id
        )


class Level:
    """
    Acts as a container for the current scene.
    Holds the background image and the list of platforms/ramps/coins that make up the environment.
    """

    __slots__ = (
        'background_image', 'level_index', 'is_last_level', 'platforms', 'platform_rects', 
        'floor_rects', 'ramps', 'coins', 'princess_coin', '_type', 
        '_cached_collision_lines', '_cached_ramp_lines', 'has_ramps', 'render_surface'
    )

    def __init__(
        self,
        bg_image_path: str,
        platforms_data: List[Platform],
        ramps_data: Optional[List[Ramp]] = None,
        coins_data: Optional[List[Coin]] = None,
        level_index: int = 0,
        is_last_level: bool = False
    ) -> None:
        """
        Initializes a Level object with background assets and environment entities.

        Args:
            bg_image_path (str): Path to background image file.
            platforms_data (List[Platform]): List of Platform objects in this level.
            ramps_data (Optional[List[Ramp]]): Optional list of Ramp objects.
            coins_data (Optional[List[Coin]]): Optional list of Coin objects.
            level_index (int): The 0-indexed level identifier.
            is_last_level (bool): Flag indicating if this is the final level.

        Returns:
            None
        """
        target_size: tuple[int, int] = (Settings.WIDTH, Settings.HEIGHT)
        loaded_bg: Optional[Surface] = None

        if bg_image_path:
            loaded_bg = AssetsManager.get_instance().load_image(bg_image_path, size=target_size)

        if loaded_bg is not None:
            self.background_image: Surface = loaded_bg
        else:
            self.background_image = Surface(target_size)
            self.background_image.fill(Colors.BG_COLOR)

        self.level_index: int = level_index
        self.is_last_level: bool = is_last_level
        self.platforms: List[Platform] = platforms_data
        self.platform_rects: List[Rect] = []
        
        for p in self.platforms:
            r: Rect = p.rect.copy()
            if r.top <= 0:
                r.top -= Settings.HEIGHT
                r.height += Settings.HEIGHT
            if r.bottom >= Settings.HEIGHT:
                r.height += Settings.HEIGHT
            self.platform_rects.append(r)

        self.floor_rects: List[Rect] = [r for r in self.platform_rects if r.width >= 20 and r.width >= r.height]

        self.ramps: List[Ramp] = ramps_data if ramps_data is not None else []
        self.coins: List[Coin] = coins_data if coins_data is not None else []
        self.princess_coin: Optional[Coin] = next((c for c in self.coins if c.is_princess), None)

        # Determine level terrain type ('snow', 'ice', or 'normal')
        if any(p.platform_type == "snow" for p in self.platforms) or any(r.ramp_type == "snow" for r in self.ramps):
            self._type: str = "snow"
        elif any(p.platform_type == "ice" for p in self.platforms) or any(r.ramp_type == "ice" for r in self.ramps):
            self._type: str = "ice"
        else:
            self._type: str = "normal"

        # cache collision lines once per level instance to optimize the fps
        self._cached_collision_lines: List[Line] = self._build_collision_lines()
        self._cached_ramp_lines: List[Line] = [l for l in self._cached_collision_lines if l.isDiagonal]
        self.has_ramps: bool = len(self._cached_ramp_lines) > 0

        self.render_surface: Surface = self.background_image.copy()
        for platform in self.platforms:
            platform.draw(self.render_surface)
        for ramp in self.ramps:
            ramp.draw(self.render_surface)

    def draw(self, surface: Surface) -> None:
        """
        Renders level geometry and active coins on the target surface.

        Args:
            surface (Surface): Target surface to render level onto.

        Returns:
            None
        """
        if Settings.ALLOW_DRAW:
            surface.blit(self.render_surface, (0, 0))
            for coin in self.coins:
                coin.draw(surface)
        else:
            surface.blit(self.background_image, (0, 0))

    def _build_collision_lines(self) -> List[Line]:
        """
        Constructs 2D collision line segments for platforms and ramps.

        Args:
            None

        Returns:
            List[Line]: List of constructed Line objects representing level boundaries.
        """
        lines: List[Line] = []
        for p in self.platforms:
            rect = p.rect
            lines.append(Line(rect.left, rect.top, rect.right, rect.top, LineType.HORIZONTAL, Direction.UP))
            lines.append(Line(rect.left, rect.bottom, rect.right, rect.bottom, LineType.HORIZONTAL, Direction.DOWN))
            lines.append(Line(rect.left, rect.top, rect.left, rect.bottom, LineType.VERTICAL, Direction.LEFT))
            lines.append(Line(rect.right, rect.top, rect.right, rect.bottom, LineType.VERTICAL, Direction.RIGHT))

        for r in self.ramps:
            lines.append(Line(r.x1, r.y1, r.x2, r.y2, LineType.DIAGONAL))

        return lines

    def get_collision_lines(self) -> List[Line]:
        """
        Returns pre-cached list of all collision line segments.

        Args:
            None

        Returns:
            List[Line]: Pre-cached collision line segments for this level.
        """
        return self._cached_collision_lines

    def get_ramp_lines(self) -> List[Line]:
        """
        Returns pre-cached list of diagonal ramp collision line segments.

        Args:
            None

        Returns:
            List[Line]: Pre-cached diagonal ramp line segments.
        """
        return self._cached_ramp_lines

    @property
    def type(self) -> str:
        """
        Returns the level terrain type ('normal', 'snow', or 'ice').

        Args:
            None

        Returns:
            str: Level terrain type.
        """
        return self._type


class LevelManager:
    """
    Manages loading, caching, and creation of Level objects.
    """
    _instance: Optional['LevelManager'] = None
    
    __slots__ = ('current_level_index', 'level_cache', 'level_data', 'max_level_index')

    def __init__(self, json_path: str = Settings.LEVEL_DATA_PATH) -> None:
        """
        Initializes LevelManager and loads level dataset from specified JSON file.

        Args:
            json_path (str): File system path to the levels JSON configuration file.

        Returns:
            None
        """
        LevelManager._instance = self
        self.current_level_index: int = Settings.START_LEVEL_INDEX
        self.level_cache: Dict[int, Level] = {}
        path: Path = Path(json_path)

        try:
            with open(path, 'r', encoding='utf-8') as file:
                self.level_data: Dict[str, Any] = load(file)
        except (FileNotFoundError, OSError):
            print(f"ERROR: The file {json_path} was not found.")
            self.level_data = {"0": {"background": "", "platforms": []}}

        valid_keys = [int(k) for k in self.level_data.keys() if k.isdigit()]
        self.max_level_index: int = max(valid_keys) if valid_keys else Settings.MAX_LEVEL_INDEX

    def get_level(self, index: int) -> Level:
        """
        Retrieves a Level object by index.

        Args:
            index (int): 0-indexed level identifier.

        Returns:
            Level: Loaded or cached Level object.
        """
        if index > self.max_level_index:
            index = self.max_level_index

        if index in self.level_cache:
            return self.level_cache[index]

        level_str: str = str(index)
        if level_str not in self.level_data:
            print(f"WARNING: Level {level_str} not found. Default level {self.max_level_index}.")
            level_str = str(self.max_level_index)
            index = self.max_level_index
            if index in self.level_cache:
                return self.level_cache[index]

        data: Dict[str, Any] = self.level_data[level_str]
        bg_path: str = data.get("background", "")

        platforms: List[Platform] = [PlatformFactory.create_platform(p_data) for p_data in data.get("platforms", [])]
        ramps: List[Ramp] = [PlatformFactory.create_ramp(r_data) for r_data in data.get("ramps", [])]
        coins: List[Coin] = [PlatformFactory.create_coin(c_data, level_index=index, coin_index=i) for i, c_data in enumerate(data.get("coins", []))]

        is_last: bool = (index == self.max_level_index)
 
        level_obj: Level = Level(
            bg_path, platforms, ramps, coins,
            level_index=index, is_last_level=is_last
        )
        self.level_cache[index] = level_obj
        
        return level_obj

    def get_current_level(self) -> Level:
        """
        Returns the currently active Level instance.

        Args:
            None

        Returns:
            Level: Currently active Level object based on current_level_index.
        """
        return self.get_level(self.current_level_index)

    @classmethod
    def get_instance(cls, json_path: str = Settings.LEVEL_DATA_PATH) -> 'LevelManager':
        """
        Retrieves or creates the singleton instance of LevelManager.

        Args:
            json_path (str): File system path to the levels JSON configuration file.

        Returns:
            LevelManager: The singleton instance.
        """
        if cls._instance is None:
            cls._instance = LevelManager(json_path)
        return cls._instance