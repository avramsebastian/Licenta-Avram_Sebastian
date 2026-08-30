from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional
from pygame import Vector2, Rect

class LineType(Enum):
    """Enumeration for classification of collision lines."""
    HORIZONTAL = auto()
    VERTICAL = auto()
    DIAGONAL = auto()

class Direction(Enum):
    """Enumeration representing surface normal collision orientation."""
    NONE = auto()
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()

@dataclass
class DiagonalCollisionInfo:
    """Data container for diagonal collision details."""

    leftSideOfPlayerCollided: bool = False
    rightSideOfPlayerCollided: bool = False
    topSideOfPlayerCollided: bool = False
    bottomSideOfPlayerCollided: bool = False
    collisionPoints: List[Vector2] = field(default_factory=list)

    def reset(self) -> None:
        """
        Resets all collision flags and clears intersection points.

        Args:
            None

        Returns:
            None
        """
        self.leftSideOfPlayerCollided = False
        self.rightSideOfPlayerCollided = False
        self.topSideOfPlayerCollided = False
        self.bottomSideOfPlayerCollided = False
        self.collisionPoints.clear()

@dataclass
class Line:
    """Represents a collision line in the physics engine."""

    x1: float
    y1: float
    x2: float
    y2: float
    type: LineType
    direction: Direction = Direction.NONE
    diagonalCollisionInfo: Optional[DiagonalCollisionInfo] = None
    bounding_rect: Rect = field(init=False)

    def __post_init__(self) -> None:
        """
        Pre-computes and caches bounding Rect for zero-allocation broadphase culling.

        Args:
            None

        Returns:
            None
        """
        min_x = min(self.x1, self.x2)
        min_y = min(self.y1, self.y2)
        w = max(1.0, abs(self.x2 - self.x1))
        h = max(1.0, abs(self.y2 - self.y1))
        self.bounding_rect = Rect(min_x, min_y, w, h)

    @property
    def isHorizontal(self) -> bool:
        """
        Checks if the line is horizontal.

        Args:
            None

        Returns:
            bool: True if LineType is HORIZONTAL, False otherwise.
        """
        return self.type == LineType.HORIZONTAL

    @property
    def isVertical(self) -> bool:
        """
        Checks if the line is vertical.

        Args:
            None

        Returns:
            bool: True if LineType is VERTICAL, False otherwise.
        """
        return self.type == LineType.VERTICAL

    @property
    def isDiagonal(self) -> bool:
        """
        Checks if the line is diagonal.

        Args:
            None

        Returns:
            bool: True if LineType is DIAGONAL, False otherwise.
        """
        return self.type == LineType.DIAGONAL