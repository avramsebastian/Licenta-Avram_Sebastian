from __future__ import annotations
from typing import Callable, Optional, Dict, Any, List
from pathlib import Path
from pygame import (
    Surface, Rect, SRCALPHA, draw, mouse,
    KEYDOWN, K_ESCAPE, SYSTEM_CURSOR_ARROW, SYSTEM_CURSOR_HAND
)
from pygame.font import SysFont, Font, init as font_init
from settings import Settings
from colors import Colors
from menu_screen import MenuButton
from stats_screen import StatsScreen
import tkinter as tk
from tkinter import filedialog
import json


class ReplayScreen:
    """
    Replay Screen displaying a 2-column grid of up to 10 loaded player JSON runs.
    Disposes all loaded run data from memory when closed.
    """
    _instance: Optional['ReplayScreen'] = None

    __slots__ = (
        'on_back', 'on_start', 'is_active', 'loaded_runs',
        'title_font', 'section_font', 'label_font', 'value_font', 'badge_font', 'btn_font', 'small_font',
        'card_width', 'card_height', 'card_x', 'card_y', 'card_rect',
        'backdrop_surface', 'dim_overlay',
        'back_button', 'start_button', 'add_button', 'grid_buttons',
        '_title_surf', '_empty_surf', '_empty_rect',
        '_lbl_file', '_lbl_time', '_lbl_gen'
    )

    def __init__(
        self,
        on_back: Optional[Callable[[], None]] = None,
        on_start: Optional[Callable[..., None]] = None
    ) -> None:
        """
        Initializes the ReplayScreen.

        Args:
            on_back (Optional[Callable[[], None]]): Callback invoked when returning to menu.
            on_start (Optional[Callable[[List[Dict[str, Any]]], None]]): Callback invoked when starting replay.
        """
        ReplayScreen._instance = self
        self.on_back: Optional[Callable[[], None]] = on_back
        self.on_start: Optional[Callable[[List[Dict[str, Any]]], None]] = on_start
        self.is_active: bool = False
        self.loaded_runs: List[Dict[str, Any]] = []

        font_init()
        try:
            self.title_font: Font = SysFont("segoeui", 26, bold=True)
            self.section_font: Font = SysFont("segoeui", 18, bold=True)
            self.label_font: Font = SysFont("segoeui", 14)
            self.value_font: Font = SysFont("segoeui", 14, bold=True)
            self.badge_font: Font = SysFont("segoeui", 16, bold=True)
            self.btn_font: Font = SysFont("segoeui", 15, bold=True)
            self.small_font: Font = SysFont("segoeui", 12)
        except Exception:
            self.title_font = Font(None, 34)
            self.section_font = Font(None, 24)
            self.label_font = Font(None, 18)
            self.value_font = Font(None, 18)
            self.badge_font = Font(None, 22)
            self.btn_font = Font(None, 20)
            self.small_font = Font(None, 16)

        self.card_width: int = 1140
        self.card_height: int = 840
        self.card_x: int = (Settings.WIDTH - self.card_width) // 2
        self.card_y: int = (Settings.HEIGHT - self.card_height) // 2
        self.card_rect: Rect = Rect(self.card_x, self.card_y, self.card_width, self.card_height)

        self.backdrop_surface: Surface = Surface((self.card_width, self.card_height), SRCALPHA)
        self.backdrop_surface.fill(Colors.STATS_CARD_BACKDROP)

        draw.rect(self.backdrop_surface, Colors.STATS_CARD_BORDER, self.backdrop_surface.get_rect(), width=2, border_radius=12)
        draw.line(self.backdrop_surface, Colors.MENU_DIVIDER_COLOR, (20, 68), (self.card_width - 20, 68), 1)

        self.dim_overlay: Surface = Surface((Settings.WIDTH, Settings.HEIGHT), SRCALPHA)
        self.dim_overlay.fill(Colors.MENU_DIM_OVERLAY)

        self._title_surf: Surface = self.title_font.render("Replay Setup", True, Colors.STATS_TITLE_COLOR)
        
        empty_text = "No runs loaded. Click 'Add Run' to select saved experiment runs (up to 10)."
        self._empty_surf: Surface = self.section_font.render(empty_text, True, Colors.STATS_LABEL_COLOR)
        self._empty_rect: Rect = self._empty_surf.get_rect(center=(self.card_rect.centerx, self.card_rect.centery + 20))

        self._lbl_file: Surface = self.small_font.render("File:", True, Colors.STATS_LABEL_COLOR)
        self._lbl_time: Surface = self.small_font.render("Total Time:", True, Colors.STATS_LABEL_COLOR)
        self._lbl_gen: Surface = self.small_font.render("Generations:", True, Colors.STATS_LABEL_COLOR)

        btn_y: int = self.card_y + 16
        back_w: int = 90
        back_x: int = self.card_x + self.card_width - back_w - 24
        self.back_button: MenuButton = MenuButton(
            Rect(back_x, btn_y, back_w, 38),
            "Back",
            self.close,
            self.btn_font
        )

        start_w: int = 90
        start_x: int = back_x - start_w - 12
        self.start_button: MenuButton = MenuButton(
            Rect(start_x, btn_y, start_w, 38),
            "Start",
            self.on_start_replay,
            self.btn_font
        )
        self.start_button.bg_color = Colors.SUCCESS_BUTTON_BG
        self.start_button.hover_bg_color = Colors.SUCCESS_BUTTON_HOVER_BG
        self.start_button.border_color = Colors.SUCCESS_BUTTON_BORDER
        self.start_button.hover_border_color = Colors.SUCCESS_BUTTON_HOVER_BORDER

        add_w: int = 110
        add_x: int = start_x - add_w - 12
        self.add_button: MenuButton = MenuButton(
            Rect(add_x, btn_y, add_w, 38),
            "Add Run",
            self.open_add_runs_dialog,
            self.btn_font
        )

        self.grid_buttons: List[tuple[MenuButton, MenuButton]] = []

    @classmethod
    def get_instance(
        cls,
        on_back: Optional[Callable[[], None]] = None,
        on_start: Optional[Callable[..., None]] = None
    ) -> 'ReplayScreen':
        """
        Retrieves or instantiates the ReplayScreen.

        Args:
            on_back (Optional[Callable[[], None]]): Optional callback update for returning to menu.
            on_start (Optional[Callable[[List[Dict[str, Any]]], None]]): Optional callback update for starting replay.

        Returns:
            ReplayScreen: The singleton instance.
        """
        if cls._instance is None:
            cls._instance = ReplayScreen(on_back, on_start)
        else:
            if on_back is not None:
                cls._instance.on_back = on_back
            if on_start is not None:
                cls._instance.on_start = on_start
        return cls._instance

    def show(self) -> None:
        """
        Activates the replay screen.
        """
        self.is_active = True

    def hide(self) -> None:
        """
        Deactivates the screen, disposes all loaded run data from memory, and resets cursor.
        """
        self.is_active = False
        self.loaded_runs.clear()
        self.grid_buttons.clear()
        try:
            mouse.set_cursor(SYSTEM_CURSOR_ARROW)
        except Exception:
            pass

    def close(self) -> None:
        """
        Closes replay screen, clears memory, and invokes the on_back navigation callback.
        """
        self.hide()
        if self.on_back is not None:
            self.on_back()

    def on_start_replay(self) -> None:
        if self.on_start is not None and self.loaded_runs:
            self.on_start(self.loaded_runs)

    def open_add_runs_dialog(self) -> None:
        """
        Opens a file picker dialog in saved_runs/ allowing selection of up to 10 total JSON files.
        """
        if len(self.loaded_runs) >= 10:
            print("Maximum limit of 10 runs already reached.")
            return

        chosen_files = []
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            initial_dir = Path("saved_runs").resolve()
            if not initial_dir.exists():
                initial_dir.mkdir(parents=True, exist_ok=True)
            chosen_files = filedialog.askopenfilenames(
                initialdir=str(initial_dir),
                title="Select Saved Run JSON Files (Max 10 total)",
                filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
            )
            root.destroy()
        except Exception as e:
            print(f"Error opening file dialog: {e}")

        if chosen_files:
            for fpath in chosen_files:
                if len(self.loaded_runs) >= 10:
                    break
                p = Path(fpath)
                if any(r["filepath"] == str(p) for r in self.loaded_runs):
                    continue
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    exp_info = data.get("experiment_info", {})
                    t_time = exp_info.get("total_time_took", "0s")
                    t_gen = exp_info.get("total_generations", 0)
                    
                    surf_fname = self.label_font.render(p.name, True, Colors.STATS_VALUE_COLOR)
                    surf_time = self.label_font.render(str(t_time), True, Colors.GOLD)
                    surf_gen = self.label_font.render(str(t_gen), True, Colors.STATS_VALUE_COLOR)
                    
                    self.loaded_runs.append({
                        "filename": p.name,
                        "filepath": str(p),
                        "data": data,
                        "total_time": t_time,
                        "total_generations": t_gen,
                        "_surf_fname": surf_fname,
                        "_surf_time": surf_time,
                        "_surf_gen": surf_gen
                    })
                except Exception as e:
                    print(f"Error loading {p.name}: {e}")

            self._rebuild_grid_buttons()

    def remove_run(self, index: int) -> None:
        """
        Removes a run from the loaded list.

        Args:
            index (int): Index of run to remove.
        """
        if 0 <= index < len(self.loaded_runs):
            del self.loaded_runs[index]
            self._rebuild_grid_buttons()

    def show_run_stats(self, index: int) -> None:
        """
        Opens the StatsScreen displaying stats for the specified run.

        Args:
            index (int): Index of run to inspect.
        """
        if 0 <= index < len(self.loaded_runs):
            self.is_active = False
            stats = StatsScreen.get_instance()
            stats.on_back = self.on_stats_back
            stats.show(self.loaded_runs[index]["data"])

    def on_stats_back(self) -> None:
        """
        Restores ReplayScreen visibility when returning from StatsScreen.
        """
        self.is_active = True

    def _rebuild_grid_buttons(self) -> None:
        """
        Recreates interactive buttons for each card in the 2-column grid and pre-renders index titles.
        """
        self.grid_buttons.clear()
        grid_x = self.card_x + 20
        grid_y = self.card_y + 80
        total_w = self.card_width - 40
        col_gap = 16
        col_w = (total_w - col_gap) // 2
        row_h = 130
        row_gap = 12

        for idx, run in enumerate(self.loaded_runs):
            col = idx % 2
            row = idx // 2
            box_x = grid_x + col * (col_w + col_gap)
            box_y = grid_y + row * (row_h + row_gap)

            btn_area_x = box_x + col_w - 125
            stats_btn_y = box_y + 24
            minus_btn_y = box_y + 70

            run["_surf_title"] = self.badge_font.render(f"Player {idx + 1}", True, Colors.STATS_HIGHLIGHT_COLOR)

            run_idx = idx
            stats_btn = MenuButton(
                Rect(btn_area_x, stats_btn_y, 110, 34),
                "Stats",
                lambda i=run_idx: self.show_run_stats(i),
                self.btn_font
            )

            minus_btn = MenuButton(
                Rect(btn_area_x, minus_btn_y, 110, 34),
                "Remove",
                lambda i=run_idx: self.remove_run(i),
                self.btn_font
            )
            minus_btn.bg_color = Colors.DANGER_BUTTON_BG
            minus_btn.hover_bg_color = Colors.DANGER_BUTTON_HOVER_BG
            minus_btn.border_color = Colors.DANGER_BUTTON_BORDER
            minus_btn.hover_border_color = Colors.DANGER_BUTTON_HOVER_BORDER

            self.grid_buttons.append((minus_btn, stats_btn))

    def handle_event(self, event) -> bool:
        """
        Processes events for the replay screen.

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

        any_hovered = False

        if self.back_button.handle_event(event):
            return True
        if self.back_button.is_hovered:
            any_hovered = True

        if self.start_button.handle_event(event):
            return True
        if self.start_button.is_hovered:
            any_hovered = True

        if self.add_button.handle_event(event):
            return True
        if self.add_button.is_hovered:
            any_hovered = True

        for minus_btn, stats_btn in self.grid_buttons:
            if minus_btn.handle_event(event) or stats_btn.handle_event(event):
                break
            if minus_btn.is_hovered or stats_btn.is_hovered:
                any_hovered = True

        try:
            mouse.set_cursor(SYSTEM_CURSOR_HAND if any_hovered else SYSTEM_CURSOR_ARROW)
        except Exception:
            pass

        return True

    def draw(self, surface: Surface) -> None:
        """
        Renders the replay screen, header buttons, and 2-column player run grid.

        Args:
            surface (Surface): Target surface.
        """
        if not self.is_active:
            return

        surface.blit(self.dim_overlay, (0, 0))
        surface.blit(self.backdrop_surface, (self.card_x, self.card_y))
        surface.blit(self._title_surf, (self.card_x + 24, self.card_y + 16))

        self.add_button.draw(surface)
        self.start_button.draw(surface)
        self.back_button.draw(surface)

        if not self.loaded_runs:
            surface.blit(self._empty_surf, self._empty_rect)
            return

        grid_x = self.card_x + 20
        grid_y = self.card_y + 80
        col_w = (self.card_width - 56) // 2  
        
        lbl_file = self._lbl_file
        lbl_time = self._lbl_time
        lbl_gen = self._lbl_gen

        for idx, run in enumerate(self.loaded_runs):
            col = idx % 2
            row = idx // 2
            box_x = grid_x + col * (col_w + 16)
            box_y = grid_y + row * 142  

            box_rect = Rect(box_x, box_y, col_w, 130)

            draw.rect(surface, Colors.STATS_ITEM_CARD_BG, box_rect, border_radius=8)
            draw.rect(surface, Colors.STATS_ITEM_CARD_BORDER, box_rect, width=1, border_radius=8)

            surface.blit(run["_surf_title"], (box_x + 16, box_y + 12))

            surface.blit(lbl_file, (box_x + 16, box_y + 40))
            surface.blit(run["_surf_fname"], (box_x + 55, box_y + 38))

            surface.blit(lbl_time, (box_x + 16, box_y + 68))
            surface.blit(run["_surf_time"], (box_x + 95, box_y + 66))

            surface.blit(lbl_gen, (box_x + 16, box_y + 96))
            surface.blit(run["_surf_gen"], (box_x + 95, box_y + 94))

            if idx < len(self.grid_buttons):
                minus_btn, stats_btn = self.grid_buttons[idx]
                stats_btn.draw(surface)
                minus_btn.draw(surface)