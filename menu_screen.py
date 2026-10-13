from __future__ import annotations
from typing import Callable, Optional, List
from pygame import Surface, Rect, SRCALPHA, draw, mouse, MOUSEBUTTONDOWN, MOUSEMOTION, SYSTEM_CURSOR_ARROW, SYSTEM_CURSOR_HAND
from pygame.font import SysFont, Font, init as font_init
from settings import Settings
from colors import Colors


class MenuButton:
    """
    Interactive button for the MenuScreen.
    """

    __slots__ = (
        'rect', 'text', 'on_click', 'is_hovered', 'font',
        'bg_color', 'hover_bg_color', 'border_color', 'hover_border_color',
        'text_color', 'hover_text_color', '_text_surf_normal', 
        '_text_surf_hover', '_text_rect'
    )

    def __init__(
        self,
        rect: Rect,
        text: str,
        on_click: Optional[Callable[[], None]] = None,
        font: Optional[Font] = None
    ) -> None:
        """
        Initializes a MenuButton instance.

        Args:
            rect (Rect): Screen bounding box rectangle.
            text (str): Display label text.
            on_click (Optional[Callable[[], None]]): Callback function invoked when clicked.
            font (Optional[Font]): Pygame font for text rendering.
        """
        self.rect: Rect = rect
        self.text: str = text
        self.on_click: Optional[Callable[[], None]] = on_click
        self.is_hovered: bool = False

        if font is None:
            font_init()
            self.font: Font = Font(None, 32)
        else:
            self.font = font

        self.bg_color: tuple[int, int, int] = Colors.BUTTON_BG
        self.hover_bg_color: tuple[int, int, int] = Colors.BUTTON_HOVER_BG
        self.border_color: tuple[int, int, int] = Colors.BUTTON_BORDER
        self.hover_border_color: tuple[int, int, int] = Colors.BUTTON_HOVER_BORDER
        self.text_color: tuple[int, int, int] = Colors.BUTTON_TEXT
        self.hover_text_color: tuple[int, int, int] = Colors.BUTTON_HOVER_TEXT

        self._text_surf_normal: Surface = self.font.render(self.text, True, self.text_color)
        self._text_surf_hover: Surface = self.font.render(self.text, True, self.hover_text_color)
        self._text_rect: Rect = self._text_surf_normal.get_rect(center=self.rect.center)

    def handle_event(self, event) -> bool:
        """
        Processes mouse interaction events.

        Args:
            event: Pygame event object.

        Returns:
            bool: True if the button was clicked, False otherwise.
        """
        if event.type == MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.on_click is not None:
                    self.on_click()
                return True
        return False

    def draw(self, surface: Surface) -> None:
        """
        Renders button background, border, and text onto the target surface.

        Args:
            surface (Surface): Target rendering surface.
        """
        bg = self.hover_bg_color if self.is_hovered else self.bg_color
        border = self.hover_border_color if self.is_hovered else self.border_color

        draw.rect(surface, bg, self.rect, border_radius=8)
        draw.rect(surface, border, self.rect, width=2, border_radius=8)

        surface.blit(self._text_surf_hover if self.is_hovered else self._text_surf_normal, self._text_rect)


class MenuScreen:
    """
    Menu screen presenting project title and navigation buttons (Save, Replay, Load, Exit).
    """

    __slots__ = (
        'is_active', 'title_font', 'subtitle_font', 'button_font',
        'card_width', 'card_height', 'card_x', 'card_y', 'card_rect',
        'backdrop_surface', 'dim_overlay', 'buttons', 
        '_title_surf', '_title_rect', '_sub_surf', '_sub_rect'
    )

    def __init__(
        self,
        on_replay: Optional[Callable[[], None]] = None,
        on_load: Optional[Callable[[], None]] = None,
        on_plot: Optional[Callable[[], None]] = None,
        on_exit: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Initializes MenuScreen.

        Args:
            on_replay (Optional[Callable[[], None]]): Handler for Replay button.
            on_load (Optional[Callable[[], None]]): Handler for Load button.
            on_plot (Optional[Callable[[], None]]): Handler for Plot button.
            on_exit (Optional[Callable[[], None]]): Handler for Exit button.
        """
        font_init()
        self.is_active: bool = False

        try:
            self.title_font: Font = SysFont("segoeui", 34, bold=True)
            self.subtitle_font: Font = SysFont("segoeui", 18)
            self.button_font: Font = SysFont("segoeui", 22, bold=True)
        except Exception:
            self.title_font = Font(None, 44)
            self.subtitle_font = Font(None, 24)
            self.button_font = Font(None, 30)

        self.card_width: int = 480
        self.card_height: int = 438
        self.card_x: int = (Settings.WIDTH - self.card_width) // 2
        self.card_y: int = (Settings.HEIGHT - self.card_height) // 2
        self.card_rect: Rect = Rect(self.card_x, self.card_y, self.card_width, self.card_height)

        self.backdrop_surface: Surface = Surface((self.card_width, self.card_height), SRCALPHA)
        self.backdrop_surface.fill(Colors.MENU_CARD_BACKDROP)

        draw.line(self.backdrop_surface, Colors.MENU_DIVIDER_COLOR, (40, 125), (self.card_width - 40, 125), 1)
        draw.rect(self.backdrop_surface, Colors.MENU_CARD_BORDER, self.backdrop_surface.get_rect(), width=2, border_radius=12)

        self.dim_overlay: Surface = Surface((Settings.WIDTH, Settings.HEIGHT), SRCALPHA)
        self.dim_overlay.fill(Colors.MENU_DIM_OVERLAY)

        self._title_surf: Surface = self.title_font.render("Jump King", True, Colors.MENU_TITLE_COLOR)
        self._title_rect: Rect = self._title_surf.get_rect(center=(self.card_rect.centerx, self.card_y + 50))

        self._sub_surf: Surface = self.subtitle_font.render("Genetic Algorithm Simulation", True, Colors.MENU_SUBTITLE_COLOR)
        self._sub_rect: Rect = self._sub_surf.get_rect(center=(self.card_rect.centerx, self.card_y + 90))

        btn_width: int = 300
        btn_height: int = 46
        btn_x: int = self.card_x + (self.card_width - btn_width) // 2
        start_btn_y: int = self.card_y + 160
        spacing: int = 16

        self.buttons: List[MenuButton] = [
            MenuButton(Rect(btn_x, start_btn_y + 0 * (btn_height + spacing), btn_width, btn_height), "Replay", on_replay, self.button_font),
            MenuButton(Rect(btn_x, start_btn_y + 1 * (btn_height + spacing), btn_width, btn_height), "Load", on_load, self.button_font),
            MenuButton(Rect(btn_x, start_btn_y + 2 * (btn_height + spacing), btn_width, btn_height), "Generate Plots", on_plot, self.button_font),
            MenuButton(Rect(btn_x, start_btn_y + 3 * (btn_height + spacing), btn_width, btn_height), "Exit", on_exit, self.button_font),
        ]

    def show(self) -> None:
        """Activates the menu screen."""
        self.is_active = True

    def hide(self) -> None:
        """Deactivates the menu screen and resets mouse cursor."""
        self.is_active = False
        try:
            mouse.set_cursor(SYSTEM_CURSOR_ARROW)
        except Exception:
            pass

    def toggle(self) -> None:
        """Toggles active visibility."""
        if self.is_active:
            self.hide()
        else:
            self.show()

    def handle_event(self, event) -> bool:
        """
        Processes events for all menu buttons when active.

        Args:
            event: Pygame event object.

        Returns:
            bool: True if an event was handled, False otherwise.
        """
        if not self.is_active:
            return False

        any_handled = False
        any_hovered = False

        for btn in self.buttons:
            if btn.handle_event(event):
                any_handled = True
            if btn.is_hovered:
                any_hovered = True

        try:
            mouse.set_cursor(SYSTEM_CURSOR_HAND if any_hovered else SYSTEM_CURSOR_ARROW)
        except Exception:
            pass

        return any_handled

    def draw(self, surface: Surface) -> None:
        """
        Renders the menu overlay, project title, and interactive buttons onto surface.

        Args:
            surface (Surface): Pygame display surface.
        """
        if not self.is_active:
            return

        surface.blit(self.dim_overlay, (0, 0))
        surface.blit(self.backdrop_surface, (self.card_x, self.card_y))
        surface.blit(self._title_surf, self._title_rect)
        surface.blit(self._sub_surf, self._sub_rect)

        for btn in self.buttons:
            btn.draw(surface)