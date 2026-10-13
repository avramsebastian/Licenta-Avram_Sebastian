from __future__ import annotations
from typing import Tuple


class Colors:
    """
    Class containg all the colors for the game.
    """

    __slots__ = ()

    # General & primaries
    WHITE: Tuple[int, int, int] = (255, 255, 255)
    BLACK: Tuple[int, int, int] = (0, 0, 0)
    GOLD: Tuple[int, int, int] = (255, 215, 0)

    # Game world & entities
    BG_COLOR: Tuple[int, int, int] = (40, 40, 40)
    PLAYER_COLOR: Tuple[int, int, int] = (255, 50, 50)
    PLATFORM_COLOR: Tuple[int, int, int] = (190, 60, 255)
    COIN_COLOR: Tuple[int, int, int] = (255, 215, 0)
    NEGATIVE_COIN_COLOR: Tuple[int, int, int] = (220, 35, 35)
    PRINCESS_COIN_COLOR: Tuple[int, int, int] = (255, 105, 180)
    PRINCESS_RIM_COLOR: Tuple[int, int, int] = (255, 215, 0)
    PRINCESS_SHINE_COLOR: Tuple[int, int, int] = (255, 255, 255)

    # Menu screen
    MENU_DIM_OVERLAY: Tuple[int, int, int, int] = (0, 0, 0, 130)
    MENU_CARD_BACKDROP: Tuple[int, int, int, int] = (18, 20, 28, 235)
    MENU_CARD_BORDER: Tuple[int, int, int] = (190, 60, 255)
    MENU_TITLE_COLOR: Tuple[int, int, int] = (255, 215, 0)
    MENU_SUBTITLE_COLOR: Tuple[int, int, int] = (180, 185, 205)
    MENU_DIVIDER_COLOR: Tuple[int, int, int] = (70, 75, 95)

    # Button 
    BUTTON_BG: Tuple[int, int, int] = (36, 40, 52)
    BUTTON_HOVER_BG: Tuple[int, int, int] = (56, 62, 82)
    BUTTON_BORDER: Tuple[int, int, int] = (75, 82, 105)
    BUTTON_HOVER_BORDER: Tuple[int, int, int] = (255, 215, 0)
    BUTTON_TEXT: Tuple[int, int, int] = (240, 240, 245)
    BUTTON_HOVER_TEXT: Tuple[int, int, int] = (255, 255, 255)

    # Stats screen
    STATS_CARD_BACKDROP: Tuple[int, int, int, int] = (16, 18, 26, 245)
    STATS_CARD_BORDER: Tuple[int, int, int] = (190, 60, 255)
    STATS_PANEL_BG: Tuple[int, int, int] = (24, 28, 40)
    STATS_PANEL_BORDER: Tuple[int, int, int] = (50, 56, 75)
    STATS_TITLE_COLOR: Tuple[int, int, int] = (255, 215, 0)
    STATS_SECTION_TITLE: Tuple[int, int, int] = (255, 255, 255)
    STATS_LABEL_COLOR: Tuple[int, int, int] = (255, 255, 255)
    STATS_VALUE_COLOR: Tuple[int, int, int] = (255, 255, 255)
    STATS_HIGHLIGHT_COLOR: Tuple[int, int, int] = (100, 220, 255)
    STATS_ITEM_CARD_BG: Tuple[int, int, int] = (30, 34, 48)
    STATS_ITEM_CARD_BORDER: Tuple[int, int, int] = (60, 68, 90)
    STATS_SUCCESS_COLOR: Tuple[int, int, int] = (80, 230, 130)

    # Action button 
    DANGER_BUTTON_BG: Tuple[int, int, int] = (70, 25, 30)
    DANGER_BUTTON_HOVER_BG: Tuple[int, int, int] = (110, 35, 45)
    DANGER_BUTTON_BORDER: Tuple[int, int, int] = (150, 45, 55)
    DANGER_BUTTON_HOVER_BORDER: Tuple[int, int, int] = (255, 75, 90)
    SUCCESS_BUTTON_BG: Tuple[int, int, int] = (25, 60, 35)
    SUCCESS_BUTTON_HOVER_BG: Tuple[int, int, int] = (35, 95, 50)
    SUCCESS_BUTTON_BORDER: Tuple[int, int, int] = (50, 130, 70)
    SUCCESS_BUTTON_HOVER_BORDER: Tuple[int, int, int] = (80, 230, 120)

    # Replay HUD 
    REPLAY_BADGE_BG: Tuple[int, int, int, int] = (20, 24, 34, 210)
    REPLAY_BADGE_TRACKED: Tuple[int, int, int] = (255, 215, 0)
    REPLAY_BADGE_NORMAL: Tuple[int, int, int] = (100, 220, 255)
