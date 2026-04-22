import pygame
from settings import Settings

class Player:
    """
    Represents the main agent in the game. 
    Handles physics, state transitions, and smooth movement logic based on strict game rules.
    """
    
    rect: pygame.Rect
    vx: float
    vy: float
    is_grounded: bool
    is_charging: bool
    facing_direction: int
    jump_charge: int

    def __init__(self, x: int, y: int) -> None:
        """
        Initializes the player's position, hitbox, velocities, and states.
        
        params:
            - x: Initial horizontal position in pixels
            - y: Initial vertical position in pixels
        """
        self.rect = pygame.Rect(x, y, 30, 30)
        self.vx = 0.0
        self.vy = 0.0
        
        self.is_grounded = False
        self.is_charging = False
        self.facing_direction = 1  
        self.jump_charge = 0

    def handle_input(self, keys: tuple) -> None:
        """
        Processes continuous keyboard input for smooth movement and reliable jump charging.
        Bypasses OS event queues to prevent holding-key bugs.
        
        params:
            - keys: A tuple/sequence of boolean values representing the current state of all keys.
        """
        if not self.is_grounded:
            return

        if keys[pygame.K_SPACE]:
            if not self.is_charging:
                self.is_charging = True
                self.jump_charge = 0
        else:
            if self.is_charging:
                self.execute_jump()

        if not self.is_charging:
            if keys[pygame.K_LEFT]:
                self.facing_direction = -1
                self.vx -= Settings.WALK_ACCEL
                if self.vx < -Settings.MAX_WALK_SPEED:
                    self.vx = -Settings.MAX_WALK_SPEED
            elif keys[pygame.K_RIGHT]:
                self.facing_direction = 1
                self.vx += Settings.WALK_ACCEL
                if self.vx > Settings.MAX_WALK_SPEED:
                    self.vx = Settings.MAX_WALK_SPEED
            else:
                self.vx *= Settings.GROUND_FRICTION
                if abs(self.vx) < 0.1:
                    self.vx = 0.0

    def update(self) -> None:
        """
        Updates the player's physics and internal states for the current frame.
        Applies gravity if airborne and handles strict jump charge accumulation if grounded.
        """
        if not self.is_grounded:
            self.vy += Settings.GRAVITY
            if self.vy > Settings.MAX_FALL_SPEED:
                self.vy = Settings.MAX_FALL_SPEED
        
        if self.is_charging and self.is_grounded:
            self.jump_charge += 1
            if self.jump_charge > Settings.MAX_JUMP_CHARGE:
                self.jump_charge = Settings.MAX_JUMP_CHARGE
            
            self.vx *= Settings.GROUND_FRICTION
            if abs(self.vx) < 0.1:
                self.vx = 0.0

    def execute_jump(self) -> None:
        """
        Calculates and applies vertical and horizontal forces based on the 
        accumulated jump charge. Includes threshold logic for micro-movements.
        """
        if self.is_grounded and self.jump_charge > 0:
            
            if self.jump_charge <= Settings.WALK_THRESHOLD:
                self.is_charging = False
                self.jump_charge = 0
                return
            
            capped_charge: int = min(self.jump_charge, Settings.MAX_JUMP_CHARGE)
            power: float = capped_charge / Settings.MAX_JUMP_CHARGE
            
            self.vy = Settings.MAX_JUMP_FORCE_Y * power
            self.vx = Settings.MAX_JUMP_FORCE_X * self.facing_direction * power
            
            self.is_grounded = False
            self.is_charging = False
            self.jump_charge = 0

    def wall_bounce(self) -> None:
        """
        Inverts horizontal velocity when hitting a wall mid-air.
        Applies a slight friction penalty to the horizontal speed.
        """
        if not self.is_grounded:
            self.vx *= -0.8
            self.facing_direction *= -1

    def draw(self, surface: pygame.Surface) -> None:
        """
        Renders the player on the given display surface.
        
        params:
            - surface: The main Pygame display surface where the player will be drawn
        """
        pygame.draw.rect(surface, Settings.PLAYER_COLOR, self.rect)