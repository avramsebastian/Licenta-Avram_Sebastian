from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional
from pygame import Vector2, Rect

class LineType(Enum):
    """Enum for classification of collision lines."""
    HORIZONTAL = auto()
    VERTICAL = auto()
    DIAGONAL = auto()

class Direction(Enum):
    """Enum representing surface normal collision orientation."""
    NONE = auto()
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()

@dataclass(slots=True)
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

@dataclass(slots=True)
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
    dx: float = field(init=False)
    dy: float = field(init=False)
    inv_dx: float = field(init=False)
    inv_dy: float = field(init=False)
    line_vec: Vector2 = field(init=False)
    p1: Vector2 = field(init=False)
    p2: Vector2 = field(init=False)

    def __post_init__(self) -> None:
        """
        Pre-computes and caches geometric constants, vectors, and bounding Rect.

        Args:
            None

        Returns:
            None
        """
        self.dx = self.x2 - self.x1
        self.dy = self.y2 - self.y1
        
        # Truth value testing is evaluated faster in CPython than explicit non-zero comparisons
        self.inv_dx = 1.0 / self.dx if self.dx else 0.0
        self.inv_dy = 1.0 / self.dy if self.dy else 0.0

        # Inline Vector2 creation to avoid unnecessary variable assignment overhead
        self.line_vec = Vector2(self.dx, self.dy).normalize() if (self.dx or self.dy) else Vector2(0, 0)
        self.p1 = Vector2(self.x1, self.y1)
        self.p2 = Vector2(self.x2, self.y2)

        # Pygame Rect creation
        self.bounding_rect = Rect(
            min(self.x1, self.x2), 
            min(self.y1, self.y2), 
            max(1.0, abs(self.dx)), 
            max(1.0, abs(self.dy))
        )

    @property
    def isHorizontal(self) -> bool:
        """
        Checks if the line is horizontal.

        Args:
            None

        Returns:
            bool: True if LineType is HORIZONTAL, False otherwise.
        """
        return self.type is LineType.HORIZONTAL

    @property
    def isVertical(self) -> bool:
        """
        Checks if the line is vertical.

        Args:
            None

        Returns:
            bool: True if LineType is VERTICAL, False otherwise.
        """
        return self.type is LineType.VERTICAL

    @property
    def isDiagonal(self) -> bool:
        """
        Checks if the line is diagonal.

        Args:
            None

        Returns:
            bool: True if LineType is DIAGONAL, False otherwise.
        """
        return self.type is LineType.DIAGONAL