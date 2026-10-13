from __future__ import annotations
from math import ceil, copysign, hypot
from typing import List, Optional, Tuple, TYPE_CHECKING
from pygame import Rect, Vector2
from geometry import DiagonalCollisionInfo, Line
from settings import Settings

if TYPE_CHECKING:
    from environment import Level
    from player import Player


class PhysicsEngine:
    """
    Physics Engine handling movement, gravity, blizzard forces,
    and hybrid Line collision for entities.
    """
    
    __slots__ = ()

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

        player.previous_pos.update(player.current_pos.x, player.current_pos.y)

        if player.fallen_timer > 0:
            player.fallen_timer -= 1
            if player.fallen_timer <= 0:
                player.has_bumped = False

        margin: int = Settings.MAX_COLLISION_CHECKS
        px: float = player.current_pos.x
        py: float = player.current_pos.y
        pw: int = player.width
        ph: int = player.height
        bx1: float = px - margin
        by1: float = py - margin
        bx2: float = px + pw + margin
        by2: float = py + ph + margin

        nearby_platforms: List[Rect] = [
            r for r in current_level.platform_rects
            if not (r.right < bx1 or r.left > bx2 or r.bottom < by1 or r.top > by2)
        ]

        has_ramps: bool = current_level.has_ramps
        nearby_ramp_lines: List[Line] = [
            l for l in current_level.get_ramp_lines()
            if not (l.bounding_rect.right < bx1 or l.bounding_rect.left > bx2 or l.bounding_rect.bottom < by1 or l.bounding_rect.top > by2)
        ] if has_ramps else []

        # Ground status check
        PhysicsEngine.check_ground_status(player, nearby_platforms, nearby_ramp_lines)

        # Pre-movement physics
        if has_ramps and nearby_ramp_lines:
            PhysicsEngine.update_player_slide(player, nearby_ramp_lines)
        else:
            player.is_sliding = False

        PhysicsEngine.apply_gravity(player)
        PhysicsEngine.apply_blizzard_force(player, current_level)
        PhysicsEngine.update_player_run(player, current_level)

        total_speed: Vector2 = player.current_speed
        vx: float = total_speed.x
        vy: float = total_speed.y

        if player.is_on_ground and not vx and not vy:
            player.previous_speed.update(vx, vy)
            PhysicsEngine.keep_in_bounds(player)
            PhysicsEngine.update_jump_timer(player)
            return

        speed_mag: float = total_speed.magnitude()
        sub_steps: int = max(1, ceil(speed_mag / 8.0))
        
        sub_vx: float = vx / sub_steps
        sub_vy: float = vy / sub_steps

        for _ in range(sub_steps):
            player.current_pos.x += sub_vx
            player.current_pos.y += sub_vy
            PhysicsEngine.resolve_collisions_hybrid(player, nearby_platforms, nearby_ramp_lines)

        player.previous_speed.update(total_speed.x, total_speed.y)

        # Post-movement boundary clamping and jump timer update
        PhysicsEngine.keep_in_bounds(player)
        PhysicsEngine.update_jump_timer(player)

    @staticmethod
    def apply_gravity(player: Player) -> None:
        """
        Applies gravity acceleration if the player is airborne.

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
        Applies wind forces on blizzard levels.

        Args:
            player (Player): Player entity instance receiving blizzard forces.
            current_level (Level): Currently active level context.

        Returns:
            None
        """
        if current_level.type != "snow":
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

        player.snow_pos = (player.snow_pos + player.blizzard_force * Settings.BLIZZARD_IMG_MULTIPLIER) % Settings.WIDTH

    @staticmethod
    def update_player_run(player: Player, current_level: Level) -> None:
        """
        Updates horizontal running depending on input and level terrain.

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
            if current_level.type == "ice":
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
            if l.isDiagonal:
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
        Verifies if player is still supported by solid ground or ramps.

        Args:
            player (Player): Player entity instance to check grounding for.
            platforms (List[Rect]): List of nearby platform Rect bounding boxes.
            ramp_lines (List[Line]): List of nearby ramp Line segments.

        Returns:
            None
        """
        if not player.is_on_ground:
            return

        f_left: float = player.current_pos.x + 1
        f_right: float = player.current_pos.x + player.width - 1
        f_top: float = player.current_pos.y + player.height
        f_bottom: float = f_top + 1

        on_something: bool = False
        for rect in platforms:
            if rect.width >= 20 and rect.width >= rect.height:
                if not (f_right <= rect.left or f_left >= rect.right or f_bottom <= rect.top or f_top >= rect.bottom):
                    on_something = True
                    break

        if not on_something and ramp_lines:
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
        if not platforms and not ramp_lines:
            return

        has_ramps: bool = bool(ramp_lines)
        player_rect: Rect = player.rect

        for _ in range(Settings.HYBRID_LOOP_LIMIT):
            collided: bool = False
            player_rect.topleft = player.current_pos

            # Ramp collisions
            if has_ramps:
                for line in ramp_lines:
                    is_hit, info = PhysicsEngine.check_line_collision(player, line)
                    if is_hit and info is not None:
                        PhysicsEngine._resolve_ramp_collision(player, line, info)
                        player_rect.topleft = player.current_pos
                        collided = True

            # Platform collisions
            for rect in platforms:
                if player_rect.colliderect(rect):
                    PhysicsEngine._resolve_platform_overlap(player, rect)
                    player_rect.topleft = player.current_pos
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
        px: float = player.current_pos.x
        py: float = player.current_pos.y
        pw: int = player.width
        ph: int = player.height
        p_right: float = px + pw
        p_bottom: float = py + ph

        top_overlap: float = p_bottom - rect.top
        bottom_overlap: float = rect.bottom - py
        left_overlap: float = p_right - rect.left
        right_overlap: float = rect.right - px

        min_overlap: float = top_overlap
        side: str = "top"
        if bottom_overlap < min_overlap:
            min_overlap = bottom_overlap
            side = "bottom"
        if left_overlap < min_overlap:
            min_overlap = left_overlap
            side = "left"
        if right_overlap < min_overlap:
            min_overlap = right_overlap
            side = "right"

        if side == "top":
            prev_bottom: float = player.previous_pos.y + ph
            was_above: bool = (prev_bottom <= rect.top + 6)
            is_horizontal_floor: bool = (rect.width >= 20 and rect.width >= rect.height)
            horizontal_overlap: bool = (p_right > rect.left + 4) and (px < rect.right - 4)

            if player.current_speed.y >= 0 and was_above and is_horizontal_floor and horizontal_overlap:
                player.current_pos.y = rect.top - ph
                player.player_landed()
                
        elif side == "bottom" and player.current_speed.y <= 0:
            player.current_pos.y = rect.bottom
            player.current_speed.y = -player.current_speed.y * 0.5
        
        elif side == "left" and player.current_speed.x >= 0:
            player.current_pos.x = rect.left - pw
            player.current_speed.x = -player.current_speed.x * 0.5
            if not player.is_on_ground:
                player.has_bumped = True
        
        elif side == "right" and player.current_speed.x <= 0:
            player.current_pos.x = rect.right
            player.current_speed.x = -player.current_speed.x * 0.5
            if not player.is_on_ground:
                player.has_bumped = True

    @staticmethod
    def _resolve_ramp_collision(player: Player, line: Line, info: Optional[DiagonalCollisionInfo]) -> None:
        """
        Ramp collision resolution depending on number of intersection points.

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
        Resolves edge to edge ramp collision where player overlaps ramp segment across 2 points.

        Args:
            player (Player): Player entity instance sliding on ramp edge.
            line (Line): Ramp Line segment being collided with.
            info (DiagonalCollisionInfo): Object containing intersection points and collision flags.

        Returns:
            None
        """
        p0 = info.collisionPoints[0]
        p1 = info.collisionPoints[1]
        mid_x: float = (p0.x + p1.x) * 0.5
        mid_y: float = (p0.y + p1.y) * 0.5

        cx: float = player.current_pos.x
        cy: float = player.current_pos.y
        if info.bottomSideOfPlayerCollided:
            cy += player.height
        if info.rightSideOfPlayerCollided:
            cx += player.width

        corr_x: float = mid_x - cx
        corr_y: float = mid_y - cy

        c_len: float = hypot(corr_x, corr_y)
        if c_len > max(player.width, player.height):
            scale: float = 5.0 / c_len
            corr_x *= scale
            corr_y *= scale

        player.current_pos.x += corr_x
        player.current_pos.y += corr_y

        line_vec: Vector2 = line.line_vec
        speed_mag: float = player.current_speed.dot(line_vec)
        player.current_speed.update(line_vec.x * speed_mag, line_vec.y * speed_mag)

        if info.topSideOfPlayerCollided:
            player.current_speed.update(0.0, 0.0)
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
        Resolves point intersection collision with a ramp endpoint or single corner.

        Args:
            player (Player): Player entity instance colliding with ramp point.
            line (Line): Ramp Line segment.
            info (DiagonalCollisionInfo): Collision metadata container.

        Returns:
            None
        """
        if not info.collisionPoints:
            return

        px: float = player.current_pos.x
        py: float = player.current_pos.y
        pw: int = player.width
        ph: int = player.height
        p_right: float = px + pw
        p_bottom: float = py + ph

        p1: Vector2 = line.p1
        p2: Vector2 = line.p2

        p1_inside: bool = (px < p1.x < p_right) and (py < p1.y < p_bottom)
        p2_inside: bool = (px < p2.x < p_right) and (py < p2.y < p_bottom)

        inside_pt: Optional[Vector2] = None
        if p1_inside:
            inside_pt = p1
        elif p2_inside:
            inside_pt = p2

        if inside_pt:
            o_top: float = p_bottom - inside_pt.y
            o_bottom: float = inside_pt.y - py
            o_left: float = p_right - inside_pt.x
            o_right: float = inside_pt.x - px

            min_overlap: float = float('inf')
            side: Optional[str] = None
            if o_top >= 0 and o_top < min_overlap:
                min_overlap = o_top
                side = "top"
            if o_bottom >= 0 and o_bottom < min_overlap:
                min_overlap = o_bottom
                side = "bottom"
            if o_left >= 0 and o_left < min_overlap:
                min_overlap = o_left
                side = "left"
            if o_right >= 0 and o_right < min_overlap:
                min_overlap = o_right
                side = "right"

            if side is None:
                return

            if side == "top" and player.current_speed.y >= 0:
                player.current_pos.y = inside_pt.y - ph - 1.0
                player.current_speed.x = PhysicsEngine._calculate_ramp_tip_push_x(inside_pt, line)
                player.current_speed.y = max(1.0, player.current_speed.y)
                player.ignore_air_friction_frames = Settings.RAMP_TIP_IGNORE_FRICTION_FRAMES
            elif side == "bottom" and player.current_speed.y <= 0:
                player.current_pos.y = inside_pt.y + Settings.COLLISION_SNAP_OFFSET
                player.current_speed.y = -player.current_speed.y * 0.5
            elif side == "left" and player.current_speed.x >= 0:
                player.current_pos.x = inside_pt.x - pw
                player.current_speed.x = -player.current_speed.x * 0.5
                if not player.is_on_ground:
                    player.has_bumped = True
            elif side == "right" and player.current_speed.x <= 0:
                player.current_pos.x = inside_pt.x + Settings.COLLISION_SNAP_OFFSET
                player.current_speed.x = -player.current_speed.x * 0.5
                if not player.is_on_ground:
                    player.has_bumped = True
        else:
            pt: Vector2 = info.collisionPoints[0]
            if info.topSideOfPlayerCollided:
                player.current_pos.y = pt.y + Settings.COLLISION_SNAP_OFFSET
                player.current_speed.y = -player.current_speed.y * 0.5
            elif info.bottomSideOfPlayerCollided:
                player.current_pos.y = pt.y - ph - Settings.COLLISION_SNAP_OFFSET - 1.0
                player.current_speed.x = PhysicsEngine._calculate_ramp_tip_push_x(pt, line)
                player.current_speed.y = max(1.0, player.current_speed.y)
                player.ignore_air_friction_frames = Settings.RAMP_TIP_IGNORE_FRICTION_FRAMES
            elif info.leftSideOfPlayerCollided:
                player.current_pos.x = pt.x + Settings.COLLISION_SNAP_OFFSET
                player.current_speed.x = -player.current_speed.x * 0.5
            elif info.rightSideOfPlayerCollided:
                player.current_pos.x = pt.x - pw - Settings.COLLISION_SNAP_OFFSET
                player.current_speed.x = -player.current_speed.x * 0.5

    @staticmethod
    def check_line_collision(player: Player, l: Line) -> Tuple[bool, Optional[DiagonalCollisionInfo]]:
        """
        Checks if player bounding rect intersects with a Line segment.

        Args:
            player (Player): Player entity instance to test.
            l (Line): Line segment to test intersection against.

        Returns:
            Tuple[bool, Optional[DiagonalCollisionInfo]]: Tuple of (is_colliding, collision_info).
        """
        if l.isDiagonal:
            return PhysicsEngine._check_diagonal_collision(player, l)

        px: float = player.current_pos.x
        py: float = player.current_pos.y
        br: Rect = l.bounding_rect
        is_hit: bool = not (px + player.width <= br.left or px >= br.right or py + player.height <= br.top or py >= br.bottom)
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
        Calculates line segment intersections between player 4 edges and a diagonal ramp Line.

        Args:
            player (Player): Player entity instance to evaluate diagonal collision for.
            l (Line): Diagonal ramp Line segment.

        Returns:
            Tuple[bool, Optional[DiagonalCollisionInfo]]: Tuple of (is_colliding, collision_info).
        """
        px: float = player.current_pos.x
        py: float = player.current_pos.y
        pw: int = player.width
        ph: int = player.height
        p_right: float = px + pw
        p_bottom: float = py + ph

        br: Rect = l.bounding_rect
        if p_right <= br.left or px >= br.right or p_bottom <= br.top or py >= br.bottom:
            return (False, None)

        x1: float = l.x1
        y1: float = l.y1
        dx: float = l.dx
        dy: float = l.dy
        inv_dx: float = l.inv_dx
        inv_dy: float = l.inv_dy

        left_hit: bool = False
        right_hit: bool = False
        top_hit: bool = False
        bottom_hit: bool = False
        pts: List[Vector2] = []

        if dx != 0:
            t = (px - x1) * inv_dx
            if 0.0 <= t <= 1.0:
                y = y1 + t * dy
                if py <= y <= p_bottom - 1:
                    left_hit = True
                    pts.append(Vector2(px, y))

        if dx != 0:
            t = (p_right - x1) * inv_dx
            if 0.0 <= t <= 1.0:
                y = y1 + t * dy
                if py <= y <= p_bottom - 1:
                    right_hit = True
                    pts.append(Vector2(p_right, y))

        if dy != 0:
            t = (py - y1) * inv_dy
            if 0.0 <= t <= 1.0:
                x = x1 + t * dx
                if px <= x <= p_right:
                    top_hit = True
                    pts.append(Vector2(x, py))

        if dy != 0:
            t = (p_bottom - 1 - y1) * inv_dy
            if 0.0 <= t <= 1.0:
                x = x1 + t * dx
                if px <= x <= p_right:
                    bottom_hit = True
                    pts.append(Vector2(x, p_bottom - 1))

        if left_hit or right_hit or top_hit or bottom_hit:
            info = DiagonalCollisionInfo(left_hit, right_hit, top_hit, bottom_hit, pts)
            return (True, info)
            
        return (False, None)