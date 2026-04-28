import pygame
from typing import Sequence, Any, List
from settings import Settings


class Player:
    def __init__(self, x: int, y: int) -> None:
        """
        Initializes the player with position, velocity, and state variables.
        
        Args:
            - x: The horizontal starting position of the player
            - y: The vertical starting position of the player
        """
        self.rect: pygame.Rect = pygame.Rect(x, y, 50, 50)
        self.vx: float = 0.0
        self.vy: float = 0.0
        self.is_grounded: bool = False
        self.is_charging: bool = False
        self.facing_direction: int = 1  
        self.jump_charge: int = 0
        self.is_ghost: bool = False
        self.on_ramp: bool = False
        self.last_ramp_slope: float = 0.0
        self._fx: float = float(x)
        self._fy: float = float(y)

    def handle_input(self, keys: pygame.key.ScancodeWrapper) -> None:
        """
        Handles player input for movement, jumping, and ghost mode.
        
        Args:
            - keys: The current state of all keyboard keys
        """
        self.is_ghost = bool(keys[pygame.K_g])
        if self.is_ghost:
            speed: int = 15
            if keys[pygame.K_LEFT]:
                self.rect.x -= speed
            if keys[pygame.K_RIGHT]:
                self.rect.x += speed
            if keys[pygame.K_UP]:
                self.rect.y -= speed
            if keys[pygame.K_DOWN]:
                self.rect.y += speed
            self.vx = 0.0
            self.vy = 0.0
            self._fx = float(self.rect.x)
            self._fy = float(self.rect.y)
            return

        if not self.is_grounded:
            return

        can_change_direction: bool = self.is_grounded and not self.on_ramp and not self.is_charging
        if can_change_direction:
            if keys[pygame.K_LEFT] and not keys[pygame.K_RIGHT]:
                self.facing_direction = -1
            elif keys[pygame.K_RIGHT] and not keys[pygame.K_LEFT]:
                self.facing_direction = 1

        if keys[pygame.K_SPACE]:
            if not self.is_charging and self.is_grounded and not self.on_ramp:
                self.is_charging = True
                self.jump_charge = 0
            elif self.is_charging and self.on_ramp:
                self.is_charging = False
                self.jump_charge = 0
        else:
            if self.is_charging:
                if not self.on_ramp:
                    self.execute_jump()
                else:
                    self.is_charging = False
                    self.jump_charge = 0

        if not self.is_charging:
            if can_change_direction and keys[pygame.K_LEFT]:
                self.vx -= Settings.WALK_ACCEL
                if self.vx < -Settings.MAX_WALK_SPEED:
                    self.vx = -Settings.MAX_WALK_SPEED
            elif can_change_direction and keys[pygame.K_RIGHT]:
                self.vx += Settings.WALK_ACCEL
                if self.vx > Settings.MAX_WALK_SPEED:
                    self.vx = Settings.MAX_WALK_SPEED
            else:
                if self.on_ramp:
                    self.vx *= Settings.RAMP_IDLE_FRICTION
                else:
                    self.vx *= Settings.GROUND_FRICTION
                if abs(self.vx) < 0.1:
                    self.vx = 0.0

    def execute_jump(self) -> None:
        """
        Executes a jump based on the current jump charge, applying appropriate velocities.
        """
        if not self.is_grounded:
            return

        if self.jump_charge <= Settings.WALK_THRESHOLD:
            self.vx = Settings.MAX_WALK_SPEED * self.facing_direction
            self.is_charging = False
            self.jump_charge = 0
            return

        raw_power: float = min(self.jump_charge, Settings.MAX_JUMP_CHARGE) / Settings.MAX_JUMP_CHARGE
        power: float = raw_power ** Settings.JUMP_CHARGE_CURVE

        vertical_speed: float = (
            Settings.MIN_JUMP_SPEED
            + (Settings.MAX_JUMP_SPEED - Settings.MIN_JUMP_SPEED) * power
        )
        self.vy = -vertical_speed

        boost: float = Settings.MIN_JUMP_SPEED_X + (Settings.MAX_JUMP_SPEED_X - Settings.MIN_JUMP_SPEED_X) * power
        self.vx = boost * self.facing_direction
        self.is_grounded = False
        self.is_charging = False
        self.on_ramp = False
        self.jump_charge = 0

    def _first_hit(self, platform_rects: Sequence[pygame.Rect], solids: Sequence[Any], ramps: Sequence[Any] = [], is_horizontal: bool = False) -> Any | None:
        """
        Checks for the first collision between the player's rectangle and a list of solid objects.

        Args:
                - platform_rects: A sequence of Pygame Rects representing the collision boxes of platforms
                - solids: A sequence of the actual platform objects corresponding to the rects, which may contain additional properties like friction
                - ramps: A sequence of ramp objects to consider for special collision logic
                - is_horizontal: A boolean indicating if this check is for horizontal movement, which affects ramp collision logic
        """
        return self._first_hit_for_rect(self.rect, platform_rects, solids, ramps, is_horizontal)

    def _first_hit_for_rect(self, rect: pygame.Rect, platform_rects: Sequence[pygame.Rect], solids: Sequence[Any], ramps: Sequence[Any] = [], is_horizontal: bool = False) -> Any | None:
        """
        Uses Pygame's optimized C-level collidelistall to detect collisions 
        against a pre-cached array of rects.

        Args:
                - rect: The Pygame Rect to check for collisions against the platforms
                - platform_rects: A sequence of Pygame Rects representing the collision boxes of platforms
                - solids: A sequence of the actual platform objects corresponding to the rects, which may contain additional properties like friction
                - ramps: A sequence of ramp objects to consider for special collision logic
                - is_horizontal: A boolean indicating if this check is for horizontal movement, which affects ramp collision logic
        """
        hit_indices: List[int] = rect.collidelistall(platform_rects)
        
        for idx in hit_indices:
            tile_rect: pygame.Rect = platform_rects[idx]
            
            if is_horizontal:
                is_under_ramp: bool = False
                for ramp in ramps:
                    for px in [rect.left, rect.centerx, rect.right]:
                        if ramp.x1 <= px <= ramp.x2:
                            ramp_y = ramp.get_y_at_x(px)
                            if ramp_y is not None and tile_rect.top >= ramp_y - 4 and rect.bottom <= ramp_y + 15:
                                is_under_ramp = True
                                break
                    if is_under_ramp: break
                
                if is_under_ramp:
                    continue
            
            return solids[idx]
            
        return None

    def _move_vertically(self, platform_rects: Sequence[pygame.Rect], solids: Sequence[Any]) -> None:
        """
        Moves the player vertically based on its vertical velocity.

        Args:
                - platform_rects: A sequence of Pygame Rects representing the collision boxes of platforms
                - solids: A sequence of the actual platform objects corresponding to the rects, which may contain additional properties like friction
        """
        self.is_grounded = False
        self._fy += self.vy
        target_y: int = int(round(self._fy))
        step_y = 1 if target_y > self.rect.y else -1 if target_y < self.rect.y else 0
        for _ in range(abs(target_y - self.rect.y)):
            self.rect.y += step_y
            hit = self._first_hit_for_rect(self.rect, platform_rects, solids)
            if hit:
                hit_rect = hit.rect
                if step_y > 0:
                    self.rect.bottom = hit_rect.top
                    self.is_grounded = True
                    self.vx *= float(getattr(hit, "friction", 1.0))
                    self.vx += float(getattr(hit, "wind_push", 0.0))
                else:
                    self.rect.top = hit_rect.bottom
                self.vy = 0.0
                self._fy = float(self.rect.y)
                break

    def _move_horizontally(self, platform_rects: Sequence[pygame.Rect], solids: Sequence[Any], ramps: Sequence[Any], was_grounded_before_move: bool) -> None:
        """
        Moves the player horizontally based on its horizontal velocity.

        Args:
                - platform_rects: A sequence of Pygame Rects representing the collision boxes of platforms
                - solids: A sequence of the actual platform objects corresponding to the rects, which may contain additional properties like friction
                - ramps: A sequence of ramp objects to consider for special collision logic
                - was_grounded_before_move: A boolean indicating if the player was grounded before this movement step, which affects wall bounce logic
        """
        self._fx += self.vx
        target_x: int = int(round(self._fx))
        step_x = 1 if target_x > self.rect.x else -1 if target_x < self.rect.x else 0
        for _ in range(abs(target_x - self.rect.x)):
            prev_rect = self.rect.copy()
            self.rect.x += step_x
            hit = self._first_hit_for_rect(self.rect, platform_rects, solids, ramps, is_horizontal=True)
            if hit:
                stepped = False
                if (self.is_grounded or was_grounded_before_move) and step_x != 0:
                    for step_up in range(1, Settings.MAX_STEP_HEIGHT + 1):
                        trial_rect = prev_rect.move(step_x, -step_up)
                        if self._first_hit_for_rect(trial_rect, platform_rects, solids, ramps, is_horizontal=True):
                            continue
                        self.rect = trial_rect
                        self._fx = float(self.rect.x)
                        self._fy = float(self.rect.y)
                        stepped = True
                        break

                if stepped:
                    continue

                hit_rect = hit.rect
                if step_x > 0:
                    if self.rect.right - hit_rect.left > 20:
                        continue
                    self.rect.right = hit_rect.left
                else:
                    if hit_rect.right - self.rect.left > 20:
                        continue
                    self.rect.left = hit_rect.right

                if not self.is_grounded and abs(self.vx) >= Settings.MIN_WALL_BOUNCE_SPEED:
                    self.vx = -self.vx * Settings.WALL_BOUNCE_DAMPING
                    self.facing_direction *= -1
                else:
                    self.vx = 0.0

                self._fx = float(self.rect.x)
                break

    def _check_ground(self, platform_rects: Sequence[pygame.Rect], solids: Sequence[Any], ramps: Sequence[Any]) -> None:
        """
        Checks if the player is currently grounded.

        Args:
                - platform_rects: A sequence of Pygame Rects representing the collision boxes of platforms
                - solids: A sequence of the actual platform objects corresponding to the rects, which may contain additional properties like friction
                - ramps: A sequence of ramp objects to consider for special collision logic
        """
        if self.vy >= 0:
            probe = self.rect.move(0, 1)
            self.is_grounded = self._first_hit_for_rect(probe, platform_rects, solids, ramps) is not None

    def _snap_to_ramps(self, ramps: Sequence[Any], was_on_ramp: bool) -> None:
        """
        Checks if the player should snap to a ramp surface.

        Args:
                - ramps: A sequence of ramp objects to consider for snapping
                - was_on_ramp: A boolean indicating if the player was on a ramp before this movement step, which affects snap logic when falling off ramps
        """
        if self.vy >= 0 or was_on_ramp:
            best_ramp = None
            best_y = None
            feet_samples = [self.rect.left + 8, self.rect.centerx, self.rect.right - 8]
            snap_dist = max(16, int(abs(self.vy)) + int(abs(self.vx * 2)) + 8)

            for ramp in ramps:
                for feet_x in feet_samples:
                    ramp_y = ramp.get_y_at_x(feet_x)
                    if ramp_y is None:
                        continue

                    if self.vx > 0 and feet_x >= ramp.x2 - Settings.RAMP_EDGE_RELEASE:
                        continue
                    if self.vx < 0 and feet_x <= ramp.x1 + Settings.RAMP_EDGE_RELEASE:
                        continue

                    if self.is_grounded and ramp_y > self.rect.bottom:
                        if feet_x != self.rect.centerx:
                            continue

                    dist = abs(self.rect.bottom - ramp_y)
                    if dist <= snap_dist:
                        if best_y is None or dist < abs(self.rect.bottom - best_y):
                            best_y = ramp_y
                            best_ramp = ramp

            if best_ramp is not None and best_y is not None:
                self.rect.bottom = int(best_y)
                self.is_grounded = True
                self.on_ramp = True

                dx = best_ramp.x2 - best_ramp.x1
                if dx != 0:
                    slope = (best_ramp.y2 - best_ramp.y1) / dx
                    self.vx += slope * Settings.RAMP_SLIDE_ACCEL
                    self.vx += (1.0 if slope > 0 else -1.0) * Settings.GRAVITY * Settings.RAMP_GRAVITY_FACTOR
                    self.vx = max(-Settings.RAMP_MAX_SPEED, min(Settings.RAMP_MAX_SPEED, self.vx))
                    self.last_ramp_slope = slope
                
                self.vy = 0.0
                self._fy = float(self.rect.y)
            else:
                if was_on_ramp and not self.is_grounded:
                    if hasattr(self, "last_ramp_slope"):
                        self.vy = self.vx * self.last_ramp_slope

    def move_and_collide(self, platform_rects: Sequence[pygame.Rect], solids: Sequence[Any], ramps: Sequence[Any] = []) -> None:
        """
        Handles the player's movement and collision resolution with solid objects and ramps.

        Args:
                - platform_rects: A sequence of Pygame Rects representing the collision boxes of platforms
                - solids: A sequence of the actual platform objects corresponding to the rects, which may contain additional properties like friction
                - ramps: A sequence of ramp objects to consider for special collision logic
        """
        was_grounded_before_move: bool = self.is_grounded or self.on_ramp
        was_on_ramp: bool = self.on_ramp
        self.on_ramp = False

        self._move_vertically(platform_rects, solids)
        self._move_horizontally(platform_rects, solids, ramps, was_grounded_before_move)
        self._check_ground(platform_rects, solids, ramps)
        self._snap_to_ramps(ramps, was_on_ramp)

        if self.rect.left < 0:
            self.rect.left = 0
            self.vx = 0.0
            self._fx = float(self.rect.x)
        elif self.rect.right > Settings.WIDTH:
            self.rect.right = Settings.WIDTH
            self.vx = 0.0
            self._fx = float(self.rect.x)

    def update(self, platform_rects: Sequence[pygame.Rect] | None = None, solids: Sequence[Any] | None = None, ramps: Sequence[Any] | None = None) -> None:
        """
        Updates the player's position and state based on velocity, gravity, and collisions.

        Args:
                - platform_rects: A sequence of Pygame Rects representing the collision boxes of platforms, or None if collision should be skipped 
                - solids: A sequence of the actual platform objects corresponding to the rects, which may contain additional properties like friction,
                          or None if collision should be skipped
                - ramps: A sequence of ramp objects to consider for special collision logic, or None if collision should be skipped
        """
        if self.is_ghost:
            self._fx = float(self.rect.x)
            self._fy = float(self.rect.y)
            return

        if not self.is_grounded:
            self.vy += Settings.GRAVITY
            if self.vy > Settings.MAX_FALL_SPEED:
                self.vy = Settings.MAX_FALL_SPEED
            self.vx *= 0.998

        if self.is_charging and self.is_grounded:
            self.jump_charge += 1
            if self.jump_charge > Settings.MAX_JUMP_CHARGE:
                self.jump_charge = Settings.MAX_JUMP_CHARGE
            if not self.on_ramp:
                self.vx *= Settings.GROUND_FRICTION

        if solids is not None and platform_rects is not None:
            self.move_and_collide(platform_rects, solids, ramps if ramps is not None else [])
        else:
            self._fx += self.vx
            self._fy += self.vy
            self.rect.x = int(round(self._fx))
            self.rect.y = int(round(self._fy))

    def sync_subpixel_position(self) -> None:
        """
        Synchronizes the player's subpixel position with its rectangle position.
        """
        self._fx = float(self.rect.x)
        self._fy = float(self.rect.y)

    def draw(self, surface: pygame.Surface) -> None:
        """
        Renders the player on the screen.
        """
        pygame.draw.rect(surface, Settings.PLAYER_COLOR, self.rect)