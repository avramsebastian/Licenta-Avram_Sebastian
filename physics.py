from __future__ import annotations
from math import ceil, copysign
from typing import List, Optional, Tuple, TYPE_CHECKING
from pygame import Rect, Vector2
from geometry import DiagonalCollisionInfo, Line
from settings import Settings

if TYPE_CHECKING:
    from environment import Level
    from player import Player


class PhysicsEngine:
    """
    Standalone Physics Engine handling movement, gravity, blizzard forces,
    and hybrid Line/AABB collision resolution for entities.
    """

    @staticmethod
    def update_entity_physics(player: Player, current_level: Level) -> None:
        """
        Executes a single physics frame update for the player entity.

        Args:
            player (Player): Player entity instance to update.
            current_level (Level): Currently active level containing environmental geometry.

        Returns:
            None
        """
        if player.is_ghost:
            return

        # Track previous frame position to validate landing direction
        player.previous_pos = player.current_pos.copy()

        if player.fallen_timer > 0:
            player.fallen_timer -= 1
            if player.fallen_timer <= 0:
                player.has_bumped = False

        ramp_lines: List[Line] = current_level.get_ramp_lines()
        platforms: List[Rect] = current_level.platform_rects

        # Filter platforms & collision lines around player
        margin: int = Settings.MAX_COLLISION_CHECKS
        broad_rect: Rect = Rect(
            player.current_pos.x - margin,
            player.current_pos.y - margin,
            player.width + margin * 2,
            player.height + margin * 2
        )
        nearby_platforms: List[Rect] = [rect for rect in platforms if broad_rect.colliderect(rect)]
        nearby_ramp_lines: List[Line] = [l for l in ramp_lines if broad_rect.colliderect(l.bounding_rect)]

        # Ground status check
        PhysicsEngine.check_ground_status(player, nearby_platforms, nearby_ramp_lines)

        # Pre-movement physics
        PhysicsEngine.update_player_slide(player, nearby_ramp_lines)
        PhysicsEngine.apply_gravity(player)
        PhysicsEngine.apply_blizzard_force(player, current_level)
        PhysicsEngine.update_player_run(player, current_level)

        # Apply sub-stepped displacement & collision resolution to eliminate tunneling when falling fast
        total_speed: Vector2 = player.current_speed
        speed_mag: float = total_speed.magnitude()
        sub_steps: int = max(1, ceil(speed_mag / 8.0))
        sub_speed: Vector2 = total_speed / sub_steps

        for _ in range(sub_steps):
            player.current_pos += sub_speed
            sub_margin: int = Settings.SUBSTEP_MARGIN
            step_broad_rect: Rect = Rect(
                player.current_pos.x - sub_margin,
                player.current_pos.y - sub_margin,
                player.width + sub_margin * 2,
                player.height + sub_margin * 2
            )
            step_platforms: List[Rect] = [rect for rect in nearby_platforms if step_broad_rect.colliderect(rect)]
            step_ramps: List[Line] = [l for l in nearby_ramp_lines if step_broad_rect.colliderect(l.bounding_rect)]
            PhysicsEngine.resolve_collisions_hybrid(player, step_platforms, step_ramps)

        player.previous_speed = total_speed.copy()

        # Post-movement boundary clamping and jump timer update
        PhysicsEngine.keep_in_bounds(player)
        PhysicsEngine.update_jump_timer(player)

    @staticmethod
    def apply_gravity(player: Player) -> None:
        """
        Applies downward gravitational acceleration if the player is airborne.

        Args:
            player (Player): Player entity instance to update gravity for.

        Returns:
            None
        """
        if not player.is_on_ground:
            player.current_speed.y += Settings.GRAVITY
            if player.current_speed.y > Settings.TERMINAL_VELOCITY:
                player.current_speed.y = Settings.TERMINAL_VELOCITY

    @staticmethod
    def apply_blizzard_force(player: Player, current_level: Level) -> None:
        """
        Applies oscillating wind forces on blizzard levels.

        Args:
            player (Player): Player entity instance receiving blizzard forces.
            current_level (Level): Currently active level context.

        Returns:
            None
        """
        if not current_level.is_blizzard_level:
            player.blizzard_force = 0.0
            return

        if abs(player.blizzard_force) >= Settings.MAX_BLIZZARD_FORCE:
            player.blizzard_timer += 1
            if player.blizzard_timer >= Settings.BLIZZARD_HOLD_TIME:
                player.blizzard_timer = 0
                player.blizzard_force_dir *= -1

        player.blizzard_force += player.blizzard_force_dir * Settings.BLIZZARD_ACCELERATION

        if player.blizzard_force > Settings.MAX_BLIZZARD_FORCE:
            player.blizzard_force = Settings.MAX_BLIZZARD_FORCE
        elif player.blizzard_force < -Settings.MAX_BLIZZARD_FORCE:
            player.blizzard_force = -Settings.MAX_BLIZZARD_FORCE

        if not player.is_on_ground:
            player.current_speed.x += player.blizzard_force

        player.snow_pos += player.blizzard_force * Settings.BLIZZARD_IMG_MULTIPLIER

    @staticmethod
    def update_player_run(player: Player, current_level: Level) -> None:
        """
        Updates horizontal running velocity depending on input and level terrain (ice vs normal).

        Args:
            player (Player): Player entity instance to update running physics for.
            current_level (Level): Currently active level context for ice detection.

        Returns:
            None
        """
        if player.jump_held:
            player.current_speed.x = 0
            return

        if player.is_on_ground and not player.is_sliding:
            if current_level.is_ice_level:
                if player.hold_dir < 0:
                    player.current_speed.x = max(-Settings.RUN_SPEED, player.current_speed.x - Settings.ICE_ACCELERATION)
                elif player.hold_dir > 0:
                    player.current_speed.x = min(Settings.RUN_SPEED, player.current_speed.x + Settings.ICE_ACCELERATION)
                else:
                    if abs(player.current_speed.x) < Settings.ICE_FRICTION:
                        player.current_speed.x = 0
                    else:
                        player.current_speed.x -= copysign(Settings.ICE_FRICTION, player.current_speed.x)
            else:
                if player.hold_dir < 0:
                    player.current_speed.x = -Settings.RUN_SPEED
                elif player.hold_dir > 0:
                    player.current_speed.x = Settings.RUN_SPEED
                else:
                    if player.ignore_air_friction_frames > 0:
                        player.ignore_air_friction_frames -= 1
                    else:
                        player.current_speed.x = 0

    @staticmethod
    def update_player_slide(player: Player, current_lines: List[Line]) -> None:
        """
        Detects if player is standing on a diagonal ramp and applies sliding physics.

        Args:
            player (Player): Player entity instance to evaluate sliding for.
            current_lines (List[Line]): Nearby collision line segments.

        Returns:
            None
        """
        on_ramp: bool = False
        for l in current_lines:
            if getattr(l, "isDiagonal", False):
                is_hit, _ = PhysicsEngine.check_line_collision(player, l)
                if is_hit:
                    on_ramp = True
                    break

        if on_ramp:
            player.is_sliding = True
            if player.current_speed.x >= 0:
                player.current_speed.x += Settings.ICE_FRICTION
            else:
                player.current_speed.x -= Settings.ICE_FRICTION
        else:
            player.is_sliding = False

    @staticmethod
    def update_jump_timer(player: Player) -> None:
        """
        Increments jump charge timer while holding jump and triggers jump at max charge.

        Args:
            player (Player): Player entity instance charging jump.

        Returns:
            None
        """
        if player.is_on_ground and player.jump_held:
            if player.jump_timer < Settings.MAX_JUMP_TIMER:
                player.jump_timer += 1
            if player.jump_timer >= Settings.MAX_JUMP_TIMER:
                player.jump_held = False
                player.perform_jump()

    @staticmethod
    def keep_in_bounds(player: Player) -> None:
        """
        Clamps player position to stay inside screen horizontal boundaries.

        Args:
            player (Player): Player entity instance to bound within screen.

        Returns:
            None
        """
        if player.current_pos.x < 0:
            player.current_pos.x = 0
            player.current_speed.x = 0
        elif player.current_pos.x > Settings.WIDTH - player.width:
            player.current_pos.x = Settings.WIDTH - player.width
            player.current_speed.x = 0

    @staticmethod
    def check_ground_status(player: Player, platforms: List[Rect], ramp_lines: List[Line]) -> None:
        """
        Verifies if player is still supported by solid ground or ramps beneath their feet.

        Args:
            player (Player): Player entity instance to check grounding for.
            platforms (List[Rect]): List of nearby platform Rect bounding boxes.
            ramp_lines (List[Line]): List of nearby ramp Line segments.

        Returns:
            None
        """
        if not player.is_on_ground:
            return

        feet_rect: Rect = Rect(player.current_pos.x + 4, player.current_pos.y + player.height - 1, max(1, player.width - 8), 3)

        on_something: bool = False
        for rect in platforms:
            if rect.width >= 20 and rect.width >= rect.height and feet_rect.colliderect(rect):
                on_something = True
                break

        if not on_something:
            for line in ramp_lines:
                is_hit, _ = PhysicsEngine.check_line_collision(player, line)
                if is_hit:
                    on_something = True
                    break

        if not on_something:
            player.is_on_ground = False
            player.jump_starting_height = (Settings.HEIGHT - player.current_pos.y) + Settings.HEIGHT * player.current_level_no

    @staticmethod
    def resolve_collisions_hybrid(player: Player, platforms: List[Rect], ramp_lines: List[Line]) -> None:
        """
        Iteratively resolves ramp and platform overlaps up to HYBRID_LOOP_LIMIT times.

        Args:
            player (Player): Player entity instance resolving collisions.
            platforms (List[Rect]): List of candidate platform bounding boxes.
            ramp_lines (List[Line]): List of candidate ramp line segments.

        Returns:
            None
        """
        for _ in range(Settings.HYBRID_LOOP_LIMIT):
            collided: bool = False
            player_rect: Rect = Rect(player.current_pos.x, player.current_pos.y, player.width, player.height)

            # Ramp Collisions
            for line in ramp_lines:
                is_hit, info = PhysicsEngine.check_line_collision(player, line)
                if is_hit and info is not None:
                    PhysicsEngine._resolve_ramp_collision(player, line, info)
                    player_rect = Rect(player.current_pos.x, player.current_pos.y, player.width, player.height)
                    collided = True

            # Platform Collisions
            for rect in platforms:
                if player_rect.colliderect(rect):
                    PhysicsEngine._resolve_platform_overlap(player, rect)
                    player_rect = Rect(player.current_pos.x, player.current_pos.y, player.width, player.height)
                    collided = True

            if not collided:
                break

    @staticmethod
    def _resolve_platform_overlap(player: Player, rect: Rect) -> None:
        """
        Resolves overlapping collisions between player bounding box and a platform Rect.

        Args:
            player (Player): Player entity instance being corrected.
            rect (Rect): Platform Rect bounding box overlapping player.

        Returns:
            None
        """
        player_rect: Rect = Rect(player.current_pos.x, player.current_pos.y, player.width, player.height)

        overlaps: Dict[str, float] = {
            "top": player_rect.bottom - rect.top,
            "bottom": rect.bottom - player_rect.top,
            "left": player_rect.right - rect.left,
            "right": rect.right - player_rect.left
        }

        side: str = min(overlaps, key=lambda k: overlaps[k])

        if side == "top":
            prev_bottom: float = getattr(player, "previous_pos", player.current_pos).y + player.height
            was_above: bool = (prev_bottom <= rect.top + 6)
            is_horizontal_floor: bool = (rect.width >= 20 and rect.width >= rect.height)
            horizontal_overlap: bool = (player_rect.right > rect.left + 4) and (player_rect.left < rect.right - 4)

            if player.current_speed.y >= 0 and was_above and is_horizontal_floor and horizontal_overlap:
                player.current_pos.y = rect.top - player.height
                player.player_landed()
            else:
                if player.current_pos.x + player.width / 2 < rect.centerx:
                    player.current_pos.x = rect.left - player.width
                else:
                    player.current_pos.x = rect.right
                player.current_speed.x = -player.current_speed.x / 2
                if not player.is_on_ground:
                    player.has_bumped = True
        elif side == "bottom" and player.current_speed.y <= 0:
            player.current_pos.y = rect.bottom
            player.current_speed.y = -player.current_speed.y / 2
        elif side == "left" and player.current_speed.x >= 0:
            player.current_pos.x = rect.left - player.width
            player.current_speed.x = -player.current_speed.x / 2
            if not player.is_on_ground:
                player.has_bumped = True
        elif side == "right" and player.current_speed.x <= 0:
            player.current_pos.x = rect.right
            player.current_speed.x = -player.current_speed.x / 2
            if not player.is_on_ground:
                player.has_bumped = True

    @staticmethod
    def _resolve_ramp_collision(player: Player, line: Line, info: Optional[DiagonalCollisionInfo]) -> None:
        """
        Dispatches ramp collision resolution depending on number of intersection points.

        Args:
            player (Player): Player entity instance colliding with ramp.
            line (Line): Ramp Line segment being collided with.
            info (Optional[DiagonalCollisionInfo]): Collision details.

        Returns:
            None
        """
        if info is None:
            info = line.diagonalCollisionInfo
        if info is None:
            return

        if len(info.collisionPoints) == 2:
            PhysicsEngine._resolve_ramp_edge(player, line, info)
        else:
            PhysicsEngine._resolve_ramp_point(player, line, info)

    @staticmethod
    def _resolve_ramp_edge(player: Player, line: Line, info: DiagonalCollisionInfo) -> None:
        """
        Resolves edge-to-edge ramp collision where player overlaps ramp segment across 2 points.

        Args:
            player (Player): Player entity instance sliding on ramp edge.
            line (Line): Ramp Line segment being collided with.
            info (DiagonalCollisionInfo): Object containing intersection points and collision flags.

        Returns:
            None
        """
        midpoint: Vector2 = (info.collisionPoints[0] + info.collisionPoints[1]) * 0.5

        player_corner: Vector2 = player.current_pos.copy()
        if info.bottomSideOfPlayerCollided:
            player_corner.y += player.height
        if info.rightSideOfPlayerCollided:
            player_corner.x += player.width

        correction: Vector2 = midpoint - player_corner

        if correction.length() > max(player.width, player.height):
            correction = correction.normalize() * 5.0

        player.current_pos += correction

        line_vec: Vector2 = Vector2(line.x2 - line.x1, line.y2 - line.y1).normalize()
        speed_mag: float = player.current_speed.dot(line_vec)
        player.current_speed = line_vec * speed_mag

        if info.topSideOfPlayerCollided:
            player.current_speed = Vector2(0, 0)
            player.is_sliding = False

    @staticmethod
    def _calculate_ramp_tip_push_x(pt: Vector2, line: Line, push_speed: float = Settings.RAMP_TIP_PUSH_SPEED) -> float:
        """
        Calculates horizontal push velocity when sliding off a ramp tip.

        Args:
            pt (Vector2): Endpoint vector of the ramp.
            line (Line): Ramp Line segment.
            push_speed (float): Magnitude of horizontal push speed.

        Returns:
            float: Horizontal push velocity (positive or negative push_speed).
        """
        is_max_y: bool = (pt.y == max(line.y1, line.y2))
        is_max_x: bool = (pt.x == max(line.x1, line.x2))
        if is_max_y:
            return push_speed if is_max_x else -push_speed
        else:
            return -push_speed if is_max_x else push_speed

    @staticmethod
    def _resolve_ramp_point(player: Player, line: Line, info: DiagonalCollisionInfo) -> None:
        """
        Resolves point-intersection collision with a ramp endpoint or single corner.

        Args:
            player (Player): Player entity instance colliding with ramp point.
            line (Line): Ramp Line segment.
            info (DiagonalCollisionInfo): Collision metadata container.

        Returns:
            None
        """
        if not info.collisionPoints:
            return

        player_rect: Rect = Rect(player.current_pos.x, player.current_pos.y, player.width, player.height)
        p1: Vector2 = Vector2(line.x1, line.y1)
        p2: Vector2 = Vector2(line.x2, line.y2)

        p1_inside: bool = (player_rect.left < p1.x < player_rect.right) and (player_rect.top < p1.y < player_rect.bottom)
        p2_inside: bool = (player_rect.left < p2.x < player_rect.right) and (player_rect.top < p2.y < player_rect.bottom)

        inside_pt: Optional[Vector2] = None
        if p1_inside:
            inside_pt = p1
        elif p2_inside:
            inside_pt = p2

        if inside_pt:
            overlaps: Dict[str, float] = {
                "top": player_rect.bottom - inside_pt.y,
                "bottom": inside_pt.y - player_rect.top,
                "left": player_rect.right - inside_pt.x,
                "right": inside_pt.x - player_rect.left
            }

            valid_overlaps: Dict[str, float] = {k: v for k, v in overlaps.items() if v >= 0}
            if not valid_overlaps:
                return

            side: str = min(valid_overlaps, key=lambda k: valid_overlaps[k])

            if side == "top" and player.current_speed.y >= 0:
                player.current_pos.y = inside_pt.y - player.height - 1.0
                player.current_speed.x = PhysicsEngine._calculate_ramp_tip_push_x(inside_pt, line)
                player.current_speed.y = max(1.0, player.current_speed.y)
                player.ignore_air_friction_frames = Settings.RAMP_TIP_IGNORE_FRICTION_FRAMES
            elif side == "bottom" and player.current_speed.y <= 0:
                player.current_pos.y = inside_pt.y + Settings.COLLISION_SNAP_OFFSET
                player.current_speed.y = -player.current_speed.y / 2
            elif side == "left" and player.current_speed.x >= 0:
                player.current_pos.x = inside_pt.x - player.width
                player.current_speed.x = -player.current_speed.x / 2
                if not player.is_on_ground:
                    player.has_bumped = True
            elif side == "right" and player.current_speed.x <= 0:
                player.current_pos.x = inside_pt.x + Settings.COLLISION_SNAP_OFFSET
                player.current_speed.x = -player.current_speed.x / 2
                if not player.is_on_ground:
                    player.has_bumped = True
        else:
            pt: Vector2 = info.collisionPoints[0]
            if info.topSideOfPlayerCollided:
                player.current_pos.y = pt.y + Settings.COLLISION_SNAP_OFFSET
                player.current_speed.y = -player.current_speed.y / 2
            elif info.bottomSideOfPlayerCollided:
                player.current_pos.y = pt.y - player.height - Settings.COLLISION_SNAP_OFFSET - 1.0
                player.current_speed.x = PhysicsEngine._calculate_ramp_tip_push_x(pt, line)
                player.current_speed.y = max(1.0, player.current_speed.y)
                player.ignore_air_friction_frames = Settings.RAMP_TIP_IGNORE_FRICTION_FRAMES
            elif info.leftSideOfPlayerCollided:
                player.current_pos.x = pt.x + Settings.COLLISION_SNAP_OFFSET
                player.current_speed.x = -player.current_speed.x / 2
            elif info.rightSideOfPlayerCollided:
                player.current_pos.x = pt.x - player.width - Settings.COLLISION_SNAP_OFFSET
                player.current_speed.x = -player.current_speed.x / 2

    @staticmethod
    def check_line_collision(player: Player, l: Line) -> Tuple[bool, Optional[DiagonalCollisionInfo]]:
        """
        Checks if player bounding rect intersects with a Line segment and returns un-shared collision info.

        Args:
            player (Player): Player entity instance to test.
            l (Line): Line segment to test intersection against.

        Returns:
            Tuple[bool, Optional[DiagonalCollisionInfo]]: Tuple of (is_colliding, collision_info).
        """
        if l.isDiagonal:
            return PhysicsEngine._check_diagonal_collision(player, l)

        rect: Rect = Rect(player.current_pos.x, player.current_pos.y, player.width, player.height)
        if l.isHorizontal:
            is_hit: bool = rect.colliderect(Rect(l.x1, l.y1, max(1.0, l.x2 - l.x1), 1.0))
            return (is_hit, None)
        else:
            is_hit: bool = rect.colliderect(Rect(l.x1, l.y1, 1.0, max(1.0, l.y2 - l.y1)))
            return (is_hit, None)

    @staticmethod
    def is_colliding_with_line(player: Player, l: Line) -> bool:
        """
        Checks if player bounding rect intersects with a Line segment.

        Args:
            player (Player): Player entity instance to test.
            l (Line): Line segment to test intersection against.

        Returns:
            bool: True if player intersects Line segment, False otherwise.
        """
        is_hit, _ = PhysicsEngine.check_line_collision(player, l)
        return is_hit

    @staticmethod
    def _check_diagonal_collision(player: Player, l: Line) -> Tuple[bool, Optional[DiagonalCollisionInfo]]:
        """
        Calculates 2D line segment intersections between player 4 edges and a diagonal ramp Line.

        Args:
            player (Player): Player entity instance to evaluate diagonal collision for.
            l (Line): Diagonal ramp Line segment.

        Returns:
            Tuple[bool, Optional[DiagonalCollisionInfo]]: Tuple of (is_colliding, collision_info).
        """
        player_rect: Rect = Rect(player.current_pos.x, player.current_pos.y, player.width, player.height)
        if not player_rect.colliderect(l.bounding_rect):
            return (False, None)

        tl: Vector2 = player.current_pos
        tr: Vector2 = Vector2(tl.x + player.width, tl.y)
        bl: Vector2 = Vector2(tl.x, tl.y + player.height - 1)
        br: Vector2 = Vector2(bl.x + player.width, bl.y)

        def intersect(p1: Vector2, p2: Vector2, p3: Vector2, p4: Vector2) -> Tuple[bool, float, float]:
            denom: float = ((p4.y - p3.y) * (p2.x - p1.x) - (p4.x - p3.x) * (p2.y - p1.y))
            if denom == 0:
                return (False, 0.0, 0.0)
            ua: float = ((p4.x - p3.x) * (p1.y - p3.y) - (p4.y - p3.y) * (p1.x - p3.x)) / denom
            ub: float = ((p2.x - p1.x) * (p1.y - p3.y) - (p2.y - p1.y) * (p1.x - p3.x)) / denom
            if 0 <= ua <= 1 and 0 <= ub <= 1:
                return (True, p1.x + ua * (p2.x - p1.x), p1.y + ua * (p2.y - p1.y))
            return (False, 0.0, 0.0)

        lp1: Vector2 = Vector2(l.x1, l.y1)
        lp2: Vector2 = Vector2(l.x2, l.y2)
        left: Tuple[bool, float, float] = intersect(tl, bl, lp1, lp2)
        right: Tuple[bool, float, float] = intersect(tr, br, lp1, lp2)
        top: Tuple[bool, float, float] = intersect(tl, tr, lp1, lp2)
        bottom: Tuple[bool, float, float] = intersect(bl, br, lp1, lp2)

        if left[0] or right[0] or top[0] or bottom[0]:
            info: DiagonalCollisionInfo = DiagonalCollisionInfo(
                leftSideOfPlayerCollided=left[0],
                rightSideOfPlayerCollided=right[0],
                topSideOfPlayerCollided=top[0],
                bottomSideOfPlayerCollided=bottom[0],
                collisionPoints=[Vector2(res[1], res[2]) for res in (left, right, top, bottom) if res[0]]
            )
            return (True, info)
        return (False, None)
