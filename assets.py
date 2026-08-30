from pathlib import Path
from typing import Dict, Optional, Tuple, Union
from pygame import Surface, display, transform, SRCALPHA, image, error
from settings import Settings


class AssetsManager:
    """
    Assets Manager singleton that loads, scales, and caches game graphics.
    Provides safe fallbacks for execution and generic image caching.
    """
    _instance: Optional['AssetsManager'] = None

    PLAYER_POSES: Tuple[str, ...] = ("idle", "squat", "jump", "fall", "fallen", "oof", "run1", "run2", "run3")

    def __init__(self) -> None:
        """
        Initializes the AssetsManager with empty caches and unloaded state.
        """
        self.player_images_right: Dict[str, Surface] = {}
        self.player_images_left: Dict[str, Surface] = {}
        self.snow_image: Optional[Surface] = None
        self._generic_cache: Dict[Tuple[str, Optional[Tuple[int, int]]], Surface] = {}
        self._loaded: bool = False

    @classmethod
    def get_instance(cls) -> 'AssetsManager':
        """
        Retrieves or creates the single shared instance of AssetsManager.

        Returns:
            AssetsManager: The singleton instance of the asset manager.
        """
        if cls._instance is None:
            cls._instance = AssetsManager()
        return cls._instance

    @staticmethod
    def _prepare_surface(surface: Surface) -> Surface:
        """
        Safely converts pixel format of a surface if display is active.

        Args:
            surface (Surface): The surface to optimize.

        Returns:
            Surface: The converted surface or original surface if display is inactive.
        """
        if display.get_surface() is not None:
            return surface.convert_alpha()
        return surface

    def load_image(self, path: Union[str, Path], size: Optional[Tuple[int, int]] = None) -> Optional[Surface]:
        """
        Generic method to load, convert, scale, and cache any image asset.

        Args:
            path (Union[str, Path]): Path to the image file.
            size (Optional[Tuple[int, int]]): Target (width, height) to scale the image.

        Returns:
            Optional[Surface]: Loaded and scaled surface, or None if loading fails.
        """
        path_str: str = str(path)
        cache_key: Tuple[str, Optional[Tuple[int, int]]] = (path_str, size)

        if cache_key in self._generic_cache:
            return self._generic_cache[cache_key]

        try:
            img: Surface = image.load(path_str)
            img = self._prepare_surface(img)
            if size is not None:
                img = transform.scale(img, size)
            self._generic_cache[cache_key] = img
            return img
        except (FileNotFoundError, error) as e:
            print(f"Warning: Could not load asset '{path_str}' - {e}")
            return None

    def load_assets(self) -> None:
        """
        Preloads, scales, and caches all player pose sprites and environmental overlays.
        """
        if self._loaded:
            return

        base_path: Path = Path("assets") / "images" / "posses"
        player_size: Tuple[int, int] = (Settings.IMAGE_SCALEX, Settings.IMAGE_SCALEY)

        # Load player sprites (right and left facing)
        name: str
        for name in self.PLAYER_POSES:
            file_path: Path = base_path / f"{name}.png"
            img: Optional[Surface] = self.load_image(file_path, size=player_size)

            if img is None:
                # Fallback surface filled with player color if the image is not found
                fallback_surf: Surface = Surface(player_size, SRCALPHA)
                fallback_surf.fill(Settings.PLAYER_COLOR)
                img = fallback_surf

            self.player_images_right[name] = img
            self.player_images_left[name] = transform.flip(img, True, False)

        # Load blizzard snow overlay
        snow_path: Path = Path("assets") / "images" / "blizzard" / "snow.png"
        snow_size: Tuple[int, int] = (Settings.WIDTH, Settings.HEIGHT)
        self.snow_image = self.load_image(snow_path, size=snow_size)

        self._loaded = True

    def get_player_sprite(self, state: str, facing_right: bool) -> Optional[Surface]:
        """
        Retrieves the appropriate player sprite for a given animation state and orientation.

        Args:
            state (str): The animation state key (e.g., 'idle', 'jump', 'fall').
            facing_right (bool): True if the player is facing right, False for left.

        Returns:
            Optional[Surface]: The surface for the sprite, defaulting to 'idle' if state is unknown.
        """
        if not self._loaded:
            self.load_assets()

        images: Dict[str, Surface] = self.player_images_right if facing_right else self.player_images_left
        return images.get(state, images.get("idle"))

    def get_snow_image(self) -> Optional[Surface]:
        """
        Retrieves the preloaded blizzard snow overlay surface.

        Returns:
            Optional[Surface]: The snow overlay surface, or None if not loaded/available.
        """
        if not self._loaded:
            self.load_assets()
        return self.snow_image
