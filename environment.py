from dataclasses import dataclass, field
from json import load
from pathlib import Path
from typing import Any, Dict, List, Optional
from pygame import Rect, Surface, draw

from assets import AssetsManager
from geometry import Direction, Line, LineType
from settings import Settings


@dataclass
class Platform:
    """
    Represents a physical platform in the game world that entities can stand on or collide with.
    """
    x: int
    y: int
    width: int
    height: int
    friction: float = 1.0
    wind_push: float = 0.0
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
        draw.rect(surface, Settings.PLATFORM_COLOR, self.rect, 3)

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


@dataclass
class Ramp:
    """
    Represents a diagonal surface in the game, defined by two points (x1, y1) and (x2, y2).
    """
    x1: int
    y1: int
    x2: int
    y2: int
    friction: float = 1.0
    wind_push: float = 0.0

    def __post_init__(self) -> None:
        """
        Ensures (x1, y1) is always the left-most point.

        Args:
            None

        Returns:
            None
        """
        if self.x1 > self.x2:
            self.x1, self.x2 = self.x2, self.x1
            self.y1, self.y2 = self.y2, self.y1

    def get_y_at_x(self, player_x: float) -> Optional[float]:
        """
        Calculates vertical Y coordinate along the ramp segment for a given X coordinate.

        Args:
            player_x (float): Horizontal position along the X-axis.

        Returns:
            Optional[float]: Calculated Y coordinate if within ramp bounds, None otherwise.
        """
        if self.x1 <= player_x <= self.x2:
            return self.y1 + (player_x - self.x1) * (self.y2 - self.y1) / (self.x2 - self.x1)
        return None

    def draw(self, surface: Surface) -> None:
        """
        Renders the ramp line segment on the target surface.

        Args:
            surface (Surface): Target surface to render onto.

        Returns:
            None
        """
        draw.line(surface, Settings.PLATFORM_COLOR, (self.x1, self.y1), (self.x2, self.y2), 4)


@dataclass
class Coin:
    """
    Collectible coin for reward shaping (positive guide coins vs negative trap coins).
    """
    x: float
    y: float
    radius: float = Settings.COIN_RADIUS
    value: float = Settings.GA_COIN_REWARD_VALUE
    is_negative: bool = False
    id: str = ""
    rect: Rect = field(init=False)

    def __post_init__(self) -> None:
        """
        Constructs the bounding Rect after dataclass initialization.
        Assigns default value and unique identifier if not specified.

        Args:
            None

        Returns:
            None
        """
        if self.is_negative and self.value == Settings.GA_COIN_REWARD_VALUE:
            self.value = Settings.GA_COIN_PENALTY_VALUE
        if not self.id:
            self.id = f"coin_{int(self.x)}_{int(self.y)}"
        self.rect = Rect(self.x - self.radius, self.y - self.radius, self.radius * 2, self.radius * 2)

    def draw(self, surface: Surface) -> None:
        """
        Renders positive coins in gold (Settings.COIN_COLOR) and negative coins in red (Settings.NEGATIVE_COIN_COLOR).

        Args:
            surface (Surface): Target surface to render onto.

        Returns:
            None
        """
        color = Settings.NEGATIVE_COIN_COLOR if (self.is_negative or self.value < 0) else Settings.COIN_COLOR
        draw.circle(surface, color, (int(self.x), int(self.y)), int(self.radius))

class PlatformFactory:
    """
    Factory Pattern: Decouples platform, ramp, and coin creation from dictionary deserialization.
    """

    @staticmethod
    def create_platform(data: Dict[str, Any]) -> Platform:
        """
        Deserializes dictionary data into a Platform instance.

        Args:
            data (Dict[str, Any]): Dictionary containing platform fields (x, y, width, height, friction, etc.).

        Returns:
            Platform: Instantiated Platform object.
        """
        return Platform(
            x=data["x"],
            y=data["y"],
            width=data["width"],
            height=data["height"],
            friction=data.get("friction", 1.0),
            wind_push=data.get("wind_push", 0.0)
        )

    @staticmethod
    def create_ramp(data: Dict[str, Any]) -> Ramp:
        """
        Deserializes dictionary data into a Ramp instance.

        Args:
            data (Dict[str, Any]): Dictionary containing ramp fields (x1, y1, x2, y2, friction, etc.).

        Returns:
            Ramp: Instantiated Ramp object.
        """
        return Ramp(
            x1=data["x1"],
            y1=data["y1"],
            x2=data["x2"],
            y2=data["y2"],
            friction=data.get("friction", 1.0),
            wind_push=data.get("wind_push", 0.0)
        )

    @staticmethod
    def create_coin(data: Dict[str, Any], level_index: int = 0, coin_index: int = 0) -> Coin:
        """
        Deserializes dictionary data into a Coin instance.

        Args:
            data (Dict[str, Any]): Dictionary containing coin fields (x, y, radius, value, is_negative, id).
            level_index (int): Index of the parent level for default ID generation.
            coin_index (int): Index of the coin in the level for default ID generation.

        Returns:
            Coin: Instantiated Coin object.
        """
        is_neg = data.get("is_negative", False) or data.get("type", "").lower() == "negative"
        default_val = Settings.GA_COIN_PENALTY_VALUE if is_neg else Settings.GA_COIN_REWARD_VALUE
        val = data.get("value", default_val)
        coin_id = data.get("id", f"coin_l{level_index}_{coin_index}_{int(data['x'])}_{int(data['y'])}")

        return Coin(
            x=data["x"],
            y=data["y"],
            radius=data.get("radius", Settings.COIN_RADIUS),
            value=val,
            is_negative=is_neg,
            id=coin_id
        )


class Level:
    """
    Acts as a container for the current scene.
    Holds the background image and the list of platforms/ramps/coins that make up the environment.
    """

    def __init__(
        self,
        bg_image_path: str,
        platforms_data: List[Platform],
        ramps_data: Optional[List[Ramp]] = None,
        coins_data: Optional[List[Coin]] = None,
        is_blizzard_level: bool = False,
        is_ice_level: bool = False
    ) -> None:
        """
        Initializes a Level object with background assets and environment entities.

        Args:
            bg_image_path (str): Path to background image file.
            platforms_data (List[Platform]): List of Platform objects in this level.
            ramps_data (Optional[List[Ramp]]): Optional list of Ramp objects.
            coins_data (Optional[List[Coin]]): Optional list of Coin objects.
            is_blizzard_level (bool): Flag indicating if blizzard wind forces are active.
            is_ice_level (bool): Flag indicating if ice friction physics are active.

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
            self.background_image.fill(Settings.BG_COLOR)

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

        self.ramps: List[Ramp] = ramps_data if ramps_data is not None else []
        self.coins: List[Coin] = coins_data if coins_data is not None else []
        self._is_blizzard_level: bool = is_blizzard_level
        self._is_ice_level: bool = is_ice_level

        # Cache collision lines once per level instance
        self._cached_collision_lines: List[Line] = self._build_collision_lines()
        self._cached_ramp_lines: List[Line] = [l for l in self._cached_collision_lines if l.isDiagonal]

    def draw(self, surface: Surface) -> None:
        """
        Renders background and all environment entities on the target surface.

        Args:
            surface (Surface): Target surface to render level onto.

        Returns:
            None
        """
        surface.blit(self.background_image, (0, 0))
        for platform in self.platforms:
            platform.draw(surface)
        for ramp in self.ramps:
            ramp.draw(surface)
        for coin in self.coins:
            coin.draw(surface)

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
            l_top: Line = Line(p.rect.left, p.rect.top, p.rect.right, p.rect.top, LineType.HORIZONTAL)
            l_top.direction = Direction.UP
            lines.append(l_top)

            l_bot: Line = Line(p.rect.left, p.rect.bottom, p.rect.right, p.rect.bottom, LineType.HORIZONTAL)
            l_bot.direction = Direction.DOWN
            lines.append(l_bot)

            l_left: Line = Line(p.rect.left, p.rect.top, p.rect.left, p.rect.bottom, LineType.VERTICAL)
            l_left.direction = Direction.LEFT
            lines.append(l_left)

            l_right: Line = Line(p.rect.right, p.rect.top, p.rect.right, p.rect.bottom, LineType.VERTICAL)
            l_right.direction = Direction.RIGHT
            lines.append(l_right)

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
    def is_blizzard_level(self) -> bool:
        """
        Returns True if the level has active blizzard/wind physics.

        Args:
            None

        Returns:
            bool: True if blizzard physics active, False otherwise.
        """
        return self._is_blizzard_level

    @property
    def is_ice_level(self) -> bool:
        """
        Returns True if the level has icy/slippery physics.

        Args:
            None

        Returns:
            bool: True if ice physics active, False otherwise.
        """
        return self._is_ice_level


class LevelManager:
    """
    Factory & Manager Pattern: Manages loading, caching, and creation of Level objects.
    """

    def __init__(self, json_path: str) -> None:
        """
        Initializes LevelManager and loads level dataset from specified JSON file.

        Args:
            json_path (str): File system path to the levels JSON configuration file.

        Returns:
            None
        """
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
        Retrieves a Level object by index, using memory caching to avoid re-parsing assets.
        Clamps index to max_level_index if out of bounds to prevent fallback to level 0.

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

        is_blizzard: bool = data.get("is_blizzard_level", False)
        is_ice: bool = data.get("is_ice_level", False)

        level_obj: Level = Level(bg_path, platforms, ramps, coins, is_blizzard, is_ice)
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