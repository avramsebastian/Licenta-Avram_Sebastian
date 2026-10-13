from __future__ import annotations
import math
from typing import Callable, Optional, Dict, Any, List
from pygame import (
    Surface, Rect, SRCALPHA, draw, mouse,
    KEYDOWN, K_ESCAPE, MOUSEWHEEL, MOUSEBUTTONDOWN,
    SYSTEM_CURSOR_ARROW, SYSTEM_CURSOR_HAND
)
from pygame.font import SysFont, Font, init as font_init
from settings import Settings
from colors import Colors
from menu_screen import MenuButton


class StatsScreen:
    """
    Stats Screen displaying detailed statistics from a loaded run JSON.
    """
    _instance: Optional['StatsScreen'] = None

    __slots__ = (
        'on_back', 'is_active', 'data', 'scroll_y', 'max_scroll',
        'title_font', 'section_font', 'label_font', 'value_font', 'badge_font', 'btn_font', 'small_font',
        'card_width', 'card_height', 'card_x', 'card_y', 'card_rect',
        'backdrop_surface', 'dim_overlay', 'back_button',
        '_title_surf', '_title_overview_surf', '_title_settings_surf', '_title_levels_surf'
    )

    def __init__(self, on_back: Optional[Callable[[], None]] = None) -> None:
        """
        Initializes the StatsScreen.

        Args:
            on_back (Optional[Callable[[], None]]): Callback invoked when returning to menu.
        """
        StatsScreen._instance = self
        self.on_back: Optional[Callable[[], None]] = on_back
        self.is_active: bool = False
        self.data: Optional[Dict[str, Any]] = None

        font_init()
        try:
            self.title_font: Font = SysFont("segoeui", 26, bold=True)
            self.section_font: Font = SysFont("segoeui", 18, bold=True)
            self.label_font: Font = SysFont("segoeui", 14)
            self.value_font: Font = SysFont("segoeui", 14, bold=True)
            self.badge_font: Font = SysFont("segoeui", 15, bold=True)
            self.btn_font: Font = SysFont("segoeui", 16, bold=True)
            self.small_font: Font = SysFont("segoeui", 12)
        except Exception:
            self.title_font = Font(None, 34)
            self.section_font = Font(None, 24)
            self.label_font = Font(None, 18)
            self.value_font = Font(None, 18)
            self.badge_font = Font(None, 20)
            self.btn_font = Font(None, 22)
            self.small_font = Font(None, 16)

        self.scroll_y: int = 0
        self.max_scroll: int = 0

        self.card_width: int = 1140
        self.card_height: int = 840
        self.card_x: int = (Settings.WIDTH - self.card_width) // 2
        self.card_y: int = (Settings.HEIGHT - self.card_height) // 2
        self.card_rect: Rect = Rect(self.card_x, self.card_y, self.card_width, self.card_height)

        self.backdrop_surface: Surface = Surface((self.card_width, self.card_height), SRCALPHA)
        self.backdrop_surface.fill(Colors.STATS_CARD_BACKDROP)

        draw.rect(self.backdrop_surface, Colors.STATS_CARD_BORDER, self.backdrop_surface.get_rect(), width=2, border_radius=12)
        draw.line(self.backdrop_surface, Colors.MENU_DIVIDER_COLOR, (20, 70), (self.card_width - 20, 70), 1)

        self.dim_overlay: Surface = Surface((Settings.WIDTH, Settings.HEIGHT), SRCALPHA)
        self.dim_overlay.fill(Colors.MENU_DIM_OVERLAY)
        
        self._title_surf: Surface = self.title_font.render("Simulation Run Statistics", True, Colors.STATS_TITLE_COLOR)
        self._title_overview_surf: Surface = self.section_font.render("Run Overview", True, Colors.STATS_SECTION_TITLE)
        self._title_settings_surf: Surface = self.section_font.render("Simulation Settings", True, Colors.STATS_SECTION_TITLE)
        self._title_levels_surf: Surface = self.section_font.render("Completed Levels Progression", True, Colors.STATS_SECTION_TITLE)

        btn_w: int = 100
        btn_h: int = 38
        btn_x: int = self.card_x + self.card_width - btn_w - 24
        btn_y: int = self.card_y + 16
        self.back_button: MenuButton = MenuButton(
            Rect(btn_x, btn_y, btn_w, btn_h),
            "Back",
            self.close,
            self.btn_font
        )

    @classmethod
    def get_instance(cls, on_back: Optional[Callable[[], None]] = None) -> 'StatsScreen':
        """
        Retrieves or instantiates the StatsScreen.

        Args:
            on_back (Optional[Callable[[], None]]): Optional callback update for returning to menu.

        Returns:
            StatsScreen: The singleton instance.
        """
        if cls._instance is None:
            cls._instance = StatsScreen(on_back)
        elif on_back is not None:
            cls._instance.on_back = on_back
        return cls._instance

    def show(self, run_data: Dict[str, Any]) -> None:
        """
        Activates the stats screen and populates it with the loaded run data.

        Args:
            run_data (Dict[str, Any]): Loaded JSON data dictionary.
        """
        self.data = run_data
        self.is_active = True
        self.scroll_y = 0
        self.max_scroll = 0
        
        exp_info = run_data.get("experiment_info", {})
        settings = exp_info.get("settings", {})
        
        start_time_val = str(exp_info.get("start_time", "Unknown"))
        if "T" in start_time_val:
            start_time_val = start_time_val.replace("T", " ").split(".")[0]

        self.data["_overview"] = [
            (self.label_font.render("Start Time:", True, Colors.STATS_LABEL_COLOR), 
             self.value_font.render(start_time_val, True, Colors.STATS_VALUE_COLOR)),
            (self.label_font.render("Total Duration:", True, Colors.STATS_LABEL_COLOR),
             self.value_font.render(str(exp_info.get("total_time_took", "0s")), True, Colors.STATS_HIGHLIGHT_COLOR)),
            (self.label_font.render("Total Generations:", True, Colors.STATS_LABEL_COLOR),
             self.value_font.render(str(exp_info.get("total_generations", 0)), True, Colors.STATS_VALUE_COLOR)),
            (self.label_font.render("Best Global Fitness:", True, Colors.STATS_LABEL_COLOR),
             self.value_font.render(str(exp_info.get("best_global_fitness", 0.0)), True, Colors.GOLD))
        ]

        strategy = settings.get("GA_MUTATION_STRATEGY", "PROGRESSIVE")

        if strategy == "PROGRESSIVE":
            mut_dir = str(settings.get("GA_MUTATION_RATE_DIRECTION", "-"))
            mut_type = str(settings.get("GA_MUTATION_RATE_TYPE", "-"))
            mut_str = str(settings.get("GA_MUTATION_RATE_STRENGTH", "-"))
            mut_sigma = str(settings.get("GA_INITIAL_SIGMA", "-"))
        else:
            mut_dir = str(settings.get("GA_REGRESSIVE_START_DIR", "-"))
            mut_type = str(settings.get("GA_REGRESSIVE_START_TYPE", "-"))
            mut_str = str(settings.get("GA_REGRESSIVE_START_STRENGTH", "-"))
            mut_sigma = str(settings.get("GA_REGRESSIVE_START_SIGMA", "-"))

        settings_list = [
            ("Population Size:", str(settings.get("GA_POPULATION_SIZE", "-"))),
            ("Genome Length:", str(settings.get("GA_GENOME_LENGTH", "-"))),
            ("Crossover Rate:", str(settings.get("GA_CROSSOVER_RATE", "-"))),
            ("Mutation Dir Rate:", mut_dir),
            ("Mutation Type Rate:", mut_type),
            ("Mutation Str Rate:", mut_str),
            ("Initial Sigma:", mut_sigma),
            ("Elitism Count:", str(settings.get("GA_ELITISM_COUNT", "-"))),
            ("Tournament Size:", str(settings.get("GA_TOURNAMENT_SIZE", "-"))),
            ("Stagnation Limit:", str(settings.get("GA_STAGNATION_THRESHOLD", "-"))),
            ("Mutation Strategy:", strategy),
            ("Active Scenario:", str(settings.get("GA_ACTIVE_SCENARIO", "-"))),
        ]
        
        self.data["_settings"] = [
            (self.small_font.render(lbl, True, Colors.STATS_LABEL_COLOR), 
             self.label_font.render(val, True, Colors.STATS_VALUE_COLOR))
            for lbl, val in settings_list
        ]
        
        levels = self.data.get("levels", [])
        for idx, lvl in enumerate(levels):
            lvl_idx = lvl.get("level_index", idx)
            lvl_num = lvl_idx + 1 if isinstance(lvl_idx, int) else lvl_idx
            gens_taken = lvl.get("generations_taken", "-")
            gene_count = lvl.get("gene_count", len(lvl.get("genes", [])))
            time_taken = lvl.get("time_taken", 0.0)

            badge_text = f"Level {lvl_num}"
            stat_str = f"Generations: {gens_taken}   |  Genes Count: {gene_count}   |   Time: {time_taken:.2f}s"
            
            lvl["_surf_badge"] = self.badge_font.render(badge_text, True, Colors.STATS_HIGHLIGHT_COLOR)
            lvl["_surf_stat"] = self.value_font.render(stat_str, True, Colors.STATS_VALUE_COLOR)

    def hide(self) -> None:
        """
        Deactivates the screen, disposes loaded data from memory, and resets cursor.
        """
        self.is_active = False
        self.data = None  
        self.scroll_y = 0
        self.max_scroll = 0
        try:
            mouse.set_cursor(SYSTEM_CURSOR_ARROW)
        except Exception:
            pass

    def close(self) -> None:
        """
        Closes stats screen and invokes the on_back navigation callback.
        """
        self.hide()
        if self.on_back is not None:
            self.on_back()

    def handle_event(self, event) -> bool:
        """
        Processes events for the stats screen.

        Args:
            event: Pygame event object.

        Returns:
            bool: True if event was handled, False otherwise.
        """
        if not self.is_active:
            return False

        if event.type == KEYDOWN and event.key == K_ESCAPE:
            self.close()
            return True

        if self.back_button.handle_event(event):
            return True

        if event.type == MOUSEWHEEL:
            self.scroll_y = max(0, min(self.max_scroll, self.scroll_y - int(event.y * 40)))
            return True

        if event.type == MOUSEBUTTONDOWN:
            if event.button == 4:
                self.scroll_y = max(0, min(self.max_scroll, self.scroll_y - 40))
                return True
            elif event.button == 5:
                self.scroll_y = max(0, min(self.max_scroll, self.scroll_y + 40))
                return True

        try:
            mouse.set_cursor(SYSTEM_CURSOR_HAND if self.back_button.is_hovered else SYSTEM_CURSOR_ARROW)
        except Exception:
            pass

        return True

    def draw(self, surface: Surface) -> None:
        """
        Renders the stats screen with experiment info and 2-column level grid.

        Args:
            surface (Surface): Target rendering surface.
        """
        if not self.is_active or self.data is None:
            return

        surface.blit(self.dim_overlay, (0, 0))
        surface.blit(self.backdrop_surface, (self.card_x, self.card_y))
        surface.blit(self._title_surf, (self.card_x + 24, self.card_y + 16))

        self.back_button.draw(surface)

        divider_y = self.card_y + 70
        self._draw_experiment_info(surface, self.card_x + 20, divider_y + 10, self.card_width - 40, 160)

        grid_y = divider_y + 180
        grid_h = self.card_y + self.card_height - grid_y - 20
        self._draw_levels_grid(surface, self.card_x + 20, grid_y, self.card_width - 40, grid_h)

    def _draw_experiment_info(self, surface: Surface, x: int, y: int, width: int, height: int) -> None:
        """
        Renders grid containing experiment overview and simulation settings.

        Args:
            surface (Surface): Target surface.
            x (int): Top-left X coordinate.
            y (int): Top-left Y coordinate.
            width (int): Total panel width.
            height (int): Total panel height.
        """
        panel_rect = Rect(x, y, width, height)
        draw.rect(surface, Colors.STATS_PANEL_BG, panel_rect, border_radius=8)
        draw.rect(surface, Colors.STATS_PANEL_BORDER, panel_rect, width=1, border_radius=8)

        ov_w = 380
        surface.blit(self._title_overview_surf, (x + 16, y + 10))

        item_y = y + 36
        for lbl_surf, val_surf in self.data["_overview"]:
            surface.blit(lbl_surf, (x + 16, item_y))
            surface.blit(val_surf, (x + 175, item_y))
            item_y += 23

        sep_x = x + ov_w + 10
        draw.line(surface, Colors.STATS_PANEL_BORDER, (sep_x, y + 10), (sep_x, y + height - 10), 1)

        settings_x = sep_x + 16
        surface.blit(self._title_settings_surf, (settings_x, y + 10))

        col_w = (width - ov_w - 50) // 3
        s_base_y = y + 36
        for idx, (lbl_s, val_s) in enumerate(self.data["_settings"]):
            c_idx = idx // 4
            r_idx = idx % 4
            curr_x = settings_x + c_idx * col_w
            curr_y = s_base_y + r_idx * 28

            surface.blit(lbl_s, (curr_x, curr_y))
            surface.blit(val_s, (curr_x, curr_y + 12))

    def _draw_levels_grid(self, surface: Surface, x: int, y: int, width: int, height: int) -> None:
        """
        Renders grid containing all level records with vertical scrolling support.

        Args:
            surface (Surface): Target surface.
            x (int): Top-left X coordinate.
            y (int): Top-left Y coordinate.
            width (int): Total grid width.
            height (int): Total grid height.
        """
        surface.blit(self._title_levels_surf, (x, y))

        levels: List[Dict[str, Any]] = self.data.get("levels", [])
        if not levels:
            empty_surf = self.label_font.render("No level progress records found in this run.", True, Colors.STATS_LABEL_COLOR)
            surface.blit(empty_surf, (x + 10, y + 40))
            return

        grid_top = y + 30
        grid_avail_h = height - 30
        num_levels = len(levels)
        num_rows = math.ceil(num_levels / 2)

        row_h = 60
        row_gap = 10
        total_content_h = num_rows * (row_h + row_gap) - row_gap if num_rows > 0 else 0
        self.max_scroll = max(0, total_content_h - grid_avail_h)
        self.scroll_y = max(0, min(self.max_scroll, self.scroll_y))

        has_scrollbar = self.max_scroll > 0
        scrollbar_gap = 16 if has_scrollbar else 0
        col_gap = 16
        col_width = (width - col_gap - scrollbar_gap) // 2

        viewport_rect = Rect(x, grid_top, width - scrollbar_gap, grid_avail_h)
        orig_clip = surface.get_clip()
        surface.set_clip(viewport_rect)

        s_y = self.scroll_y
        for idx, lvl in enumerate(levels):
            col = 0 if idx < num_rows else 1
            row = idx if col == 0 else idx - num_rows

            card_x = x + col * (col_width + col_gap)
            card_y = grid_top + row * (row_h + row_gap) - s_y

            if card_y + row_h < grid_top or card_y > grid_top + grid_avail_h:
                continue

            card_rect = Rect(card_x, card_y, col_width, row_h)
            draw.rect(surface, Colors.STATS_ITEM_CARD_BG, card_rect, border_radius=6)
            draw.rect(surface, Colors.STATS_ITEM_CARD_BORDER, card_rect, width=1, border_radius=6)

            surface.blit(lvl["_surf_badge"], (card_x + 12, card_y + 12))
            surface.blit(lvl["_surf_stat"], (card_x + 130, card_y + 12))

        surface.set_clip(orig_clip)

        if has_scrollbar:
            sb_w = 6
            sb_x = x + width - sb_w
            sb_y = grid_top
            sb_h = grid_avail_h
            draw.rect(surface, Colors.STATS_PANEL_BORDER, (sb_x, sb_y, sb_w, sb_h), border_radius=3)

            thumb_h = max(24, int(sb_h * (grid_avail_h / total_content_h)))
            thumb_y = sb_y + int((self.scroll_y / self.max_scroll) * (sb_h - thumb_h))
            draw.rect(surface, Colors.STATS_HIGHLIGHT_COLOR, (sb_x, thumb_y, sb_w, thumb_h), border_radius=3)