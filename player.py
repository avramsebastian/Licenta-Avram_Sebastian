import pygame
from settings import Settings

class Player:
    """
    Represents the main agent in the game. 
    Handles physics, state transitions, and movement logic based on strict game rules.
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

    def update(self) -> None:
        """
        Updates the player's physics and internal states for the current frame.
        Applies gravity if airborne and handles jump charge accumulation if grounded.
        Does not apply position changes directly.
        """
        if not self.is_grounded:
            self.vy += Settings.GRAVITY
            if self.vy > Settings.MAX_FALL_SPEED:
                self.vy = Settings.MAX_FALL_SPEED
        
        if self.is_charging and self.is_grounded:
            self.jump_charge += 1
            if self.jump_charge > Settings.MAX_JUMP_CHARGE:
                self.jump_charge = Settings.MAX_JUMP_CHARGE
            self.vx = 0.0  

    def move(self, direction: int) -> None:
        """
        Initiates horizontal movement. Only works if the player is on the ground 
        and not currently charging a jump.
        
        params:
            - direction: Integer indicating movement direction (1 for right, -1 for left)
        """
        if self.is_grounded and not self.is_charging:
            self.facing_direction = direction
            self.vx = Settings.WALK_SPEED * direction

    def stop_moving(self) -> None:
        """
        Stops horizontal movement by setting horizontal velocity to zero.
        """
        if self.is_grounded and not self.is_charging:
            self.vx = 0.0

    def start_charging(self) -> None:
        """
        Begins the jump charge sequence and halts any horizontal movement.
        """
        if self.is_grounded:
            self.is_charging = True
            self.vx = 0.0

    def execute_jump(self) -> None:
        """
        Calculates and applies vertical and horizontal forces based on the 
        accumulated jump charge. Transitions the player to the airborne state.
        """
        if self.is_grounded and self.jump_charge > 0:
            power: float = self.jump_charge / Settings.MAX_JUMP_CHARGE
            
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