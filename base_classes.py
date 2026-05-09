import pygame
import math
import random
from constants import *

class BasicObject(): 

# De meest fundamentele klasse. Elk object heeft een positie, alle andere klassen erven hiervan (direct of indirect)

    def __init__(self,pos: pygame.Vector2 = 0):
        self.pos = pygame.math.Vector2(pos)
        self._is_moving = isinstance(self, MovingObject)
        self._is_visual = isinstance(self, VisualObject)
        self._is_physics  = isinstance(self,PhysicsObject)
    def update(self):
        pass # Lege methode, zodat super().update() altijd werkt

    def pre_update(self):
        pass # idem, deze methode wordt aangeroepen voor update()
    def kys(self):
        waste_bin.append(self)         
class VisualObject(BasicObject):
# Object met zichtbare afbeelding, erft van BasicObject() -> heeft pos + image
    heal_animation_length = 80
    def __init__(self, image: pygame.Surface, **kwargs):
            if isinstance(image, str):
                image = pygame.image.load(image).convert_alpha()
            super().__init__(**kwargs)
            self.image = image
            self.base_image = self.image  # bewaar origineel voor rotaties
            self.animation_state = None
            self.animation_ticker = 0
            self.ticker_start = 0
    def get_frame_pos(self) -> pygame.Vector2:
        offset = pygame.math.Vector2(self.image.get_width() // 2, self.image.get_height() // 2)
        return self.pos - offset
    def animate(self):
        if self.animation_state == 'healing':
            progress = (self.ticker_start - self.animation_ticker)/self.ticker_start
            self.image = self.pulse_animation_frame(self.image, progress, (99, 245, 66))
            return
        if self.animation_state == 'charge_up':
            progress = self.animation_ticker/self.__class__.heal_animation_length
            self.image = self.pulse_animation_frame(self.image, progress , self.__class__.theme_colour)
            return
        if self.animation_state == 'shield':
            progress = (self.ticker_start - self.animation_ticker)/self.ticker_start
            self.image = self.pulse_animation_frame(self.image, progress, (40, 79, 235))
            return
    def heal_animation(self):
        self.animation_ticker = self.__class__.heal_animation_length
        self.ticker_start = self.animation_ticker
        self.animation_state = 'healing'
    def charge_up_animation(self,length):
        self.animation_ticker = length
        self.ticker_start = self.animation_ticker
        self.animation_state = 'charge_up'
    def shield_animation(self,length):
        self.animation_ticker = length
        self.ticker_start = self.animation_ticker
        self.animation_state = 'shield'
    def update(self):
        if self.animation_ticker > 0:
            self.animate()
            self.animation_ticker -= 1
        super().update()
    def pulse_animation_frame(self, base_image, progress, colour):
            w, h = base_image.get_size()
            cx, cy = w // 2, h // 2
            
            # Radii and Alpha based on 0.0 -> 1.0 progress
            outer_radius = int(progress * max(w, h))
            inner_radius = max(0, outer_radius - 10)
            alpha = int(255 * (1 - progress))
            
            if outer_radius <= 0:
                return base_image.copy()
    
            # Create a temp surface for the ring
            donut = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.circle(donut, (255,255,255, alpha/ 2), (cx, cy), outer_radius)
            pygame.draw.circle(donut, (*colour, alpha), (cx, cy), outer_radius)
            if inner_radius > 0:
                # Cut the center out
                pygame.draw.circle(donut, (0, 0, 0, 0), (cx, cy), inner_radius)
            
            # MASKING: Only show the donut where the base_image is visible
            # We blit the base_image onto the donut using BLEND_RGBA_MULT
            mask = base_image.copy()
            donut.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            
            # Combine with original
            result = base_image.copy()
            result.blit(donut, (0, 0),special_flags=pygame.BLEND_RGB_ADD)
            return result
class MovingObject(BasicObject):
    """
    Een object dat beweegt via physics:
      pos  = positie
      vel  = snelheid (velocity)
      acc  = versnelling (acceleration)
    Bij elk frame wordt pos bijgewerkt via de bewegingsvergelijking.
    """

    def __init__(self,vel = 0,acc = 0,**kwargs):
        super().__init__(**kwargs)
        self.vel = pygame.Vector2(vel)
        self.acc = pygame.Vector2(acc)

    def next_pos(self,steps = 1):
        # Berekent de positie na "steps" (kinematica)
        return self.pos + self.vel * timestep * steps + 0.5 * self.acc * (timestep * steps) ** 2

    def next_vel(self,steps = 1):
        # Berekent snelheid na "steps" (kinematica)
        return self.vel + self.acc * timestep*steps
    
    def update(self):
        
        self.vel = self.next_vel()
        if self.vel.magnitude_squared() != 0:
            self.vel = self.vel.clamp_magnitude(1500)
        self.pos = self.next_pos()
        super().update()
class GravityObject(BasicObject):
    # Object voor berekenen zwaartekrachten
    grav_ticker = 3 # how many frames gravity gets recalculated
    def __init__(self, mass: int = 200, **kwargs):
        super().__init__(**kwargs)
        self.mass = mass
        self.grav_calc_ticker = random.randint(0,self.__class__.grav_ticker)
        if isinstance(self, Planet): self.reaction_f = pygame.Vector2(0) # this is a var used to lower grav calc using action-reaction principle
        if isinstance(self, MovingObject):
            self.force = pygame.Vector2(0)

    def get_grav(self, other: "GravityObject"):
        # Berekent de zwaartekrachtsvector
        if self._is_bullet and self.source == other: return (0,0)
        if self.pos == other.pos or not self._is_moving:
            return
        diff = other.pos - self.pos
        dist_sq = diff.magnitude_squared()
        if dist_sq > 2000 ** 2:
            return  # Te ver weg: geen invloed

        # Standaard gravitatiewet: F = G * m1 * m2 / r²  (als vector)
        f = grav_cte * self.mass * other.mass * diff / dist_sq ** 1.5

        if self._is_spaceship:
            f += grav_cte * 0.01 * self.mass * other.mass * diff / dist_sq ** 1.3
        
        
        return f
        
    def get_total_gravity(self):
        # Som van alle gravitatiekrachten van elk object
        is_enemy = self._is_enemy
        if is_enemy:
            strongest_grav = 0
            strongest_grav_source = None
        if self._is_planet:
            force = self.reaction_f
            self.reaction_f = pygame.Vector2(0)
        else:
            force = pygame.Vector2(0)
        
        for planet in planets: #planets is a global, changed from active_objects to improve performance
            if planet is self:
                continue
            if self._is_planet and id(self) > id(planet):
                continue  # handled already via reaction_f
            grav = self.get_grav(planet) or (0, 0)
            if self._is_planet:
                planet.reaction_f -= grav
            if is_enemy:
                grav_mag = grav[0] ** 2 + grav[1] ** 2
                if  grav_mag > strongest_grav:
                    strongest_grav = grav_mag
                    strongest_grav_source = planet                    
            force += grav
        if is_enemy:self.strongest_grav = strongest_grav_source
        return force

    def pre_update(self):
        # Wordt elke frame vóór update() aangeroepen om acc bij te werken.
        if  self._is_moving:
            
            if  self.grav_calc_ticker == 0:
                self.force = self.get_total_gravity()
                self.acc = self.force / self.mass
                self.grav_calc_ticker = self.__class__.grav_ticker
            else:
                self.grav_calc_ticker -= 1
        super().pre_update() 
class RotatingObject(BasicObject):
    # Een object dat kan draaien.
    # angle        = huidige hoek in graden
    # angle_moment = draaisnelheid (zoals vel maar voor rotatie)
    def __init__(self,angle,angle_moment = 0,**kwargs):
         super().__init__(**kwargs)
         self.angle = angle
         self.angle_moment = angle_moment

    def angle_dampen(self):
        # Begrenst de draaisnelheid en vertraagt langzaam naar 0
        self.angle_moment = pygame.math.clamp(self.angle_moment, -250, 250)
        if self.angle_moment > 0: self.angle_moment -= 2
        if self.angle_moment < 0: self.angle_moment += 2

    def update(self):
        new_angle = self.angle + self.angle_moment*timestep
        if self._is_visual: self.image = pygame.transform.rotozoom(self.base_image, new_angle, 1)
        self.angle = new_angle
        super().update()
class Hitbox(BasicObject):
    # Basisklasse voor botsingsdetectie
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self._is_circular = isinstance(self, CircularHitbox)
        self._is_line = isinstance(self, LineHitbox)
    def hit(self,other: 'Hitbox') -> bool:
        pass
class LineHitbox(Hitbox):
    def __init__(self,start_pos:pygame.Vector2,end_pos:pygame.Vector2):
        super().__init__(pos=start_pos)
        self.end = end_pos
        self.minx = min(self.pos.x,self.end.x)
        self.miny = min(self.pos.y,self.end.y)
        self.maxx = max(self.pos.x,self.end.x)
        self.maxy = max(self.pos.y,self.end.y)
    def hit(self,other):
        if self.pos == self.end: return False
        if other._is_line:
            #currenlty unused, may be faulthy
            # bounding box check first (cheap)
            if self.minx > other.maxx or self.maxx < other.minx:
                return False
            if self.miny > other.maxy or self.maxy < other.miny:
                return False

            # cross product straddle check
            d1 = self.end - self.pos
            d2 = other.end - other.pos
            
            def cross2d(a, b):
                return a.x * b.y - a.y * b.x
            
            denom = cross2d(d1, d2)
            if denom == 0:
                return False  # parallel
            
            t = cross2d(other.pos - self.pos, d2) / denom
            u = cross2d(other.pos - self.pos, d1) / denom
            # intersection happens at self.pos + d1 * t or other.pos + d2 * u
            print(u,t)
            return 0 <= t <= 1 and 0 <= u <= 1
        if other._is_circular:
            d = self.end - self.pos
            t = ((other.pos - self.pos) * d )/ (d*d)
            t = max(0.0, min(1.0, t))
            closest = self.pos + d * t
            return (closest - other.pos).magnitude_squared() <= other.hitbox_radius ** 2
class CircularHitbox(Hitbox):
    # Ronde hitbox: botst als de afstand kleiner is dan de som van de radiussen
    def __init__(self,radius,**kwargs):
        super().__init__(**kwargs)
        self.hitbox_radius = radius

    def hit(self,other)-> bool:
        if other._is_circular:
            return (self.pos - other.pos).magnitude_squared() <= (self.hitbox_radius + other.hitbox_radius)**2 
        if other._is_line:
            return other.hit(self)
class PhysicsObject(GravityObject,MovingObject,CircularHitbox):
    # Combineert zwaartekracht + beweging + botsingsdetectie. Dit is de basis voor planeten en spaceships.
    def __init__(self, pos,vel = 0, force = 0, mass = 20, hitbox_radius = 20, **kwargs):
        super().__init__(pos=pos,vel=vel, mass=mass, radius = hitbox_radius, **kwargs)
        self._is_planet = isinstance(self, Planet)
        self._is_spaceship = isinstance(self, Spaceship)
        self._is_enemy = isinstance(self, BaseEnemy)
        self._is_bullet = isinstance(self, BaseBullet)
        self._is_predictor = isinstance(self, Predictor)
        self._is_target = isinstance(self, Target)
        self._is_player = isinstance(self, Player)
        self._is_item = isinstance(self, Item)
    def elastic_collision(self, other,energy_dis = 1, reflective = True , damage_multiplier = 0):
         """
        Verwerkt een elastische botsing tussen dit object en "other".
        energy_dis < 1 = energie gaat verloren (inelastisch)
        energy_dis > 1 = energie wordt toegevoegd (explosief)
         """
         if other.pos == self.pos:
             return
         
         # Normal vector along collision axis
         relative = (other.pos - self.pos)
         normal = relative.normalize()
         overlap = relative.magnitude() - self.hitbox_radius - other.hitbox_radius
     
         # Relative velocity along normal
         rel_vel = self.vel - other.vel
         vel_along_normal = rel_vel.dot(normal)
         
         if vel_along_normal < 0:
             return # objects are moving apart
        
         # Elastic impulse scalar
         impulse = (2 * vel_along_normal) / (self.mass + other.mass)
         
         
         if damage_multiplier != 0:
             damage = int(vel_along_normal/100 - 4)  * damage_multiplier  # pas 100 aan voor meer of minder schade; 100 px/s = 1 HP
             if damage > 0:
                 if self._is_spaceship: self.take_damage(damage)
                 if other._is_spaceship: other.take_damage(damage)
         
         impulse = impulse * energy_dis
         # Apply impulse
         self.vel -= impulse * other.mass * normal
         self.pos += normal*0.51*overlap

         if other._is_moving and reflective:
             other.vel += impulse * self.mass * normal
             other.pos -= normal*0.51*overlap
        
    def pre_update(self):
        if not chunkmanager.in_safezone(self.pos):
            try:
                chunkmanager.all_chunks[chunkmanager.get_chunk(self.pos)].append(self)
                if debug_world_gen and not self._is_predictor:
                    print(f'unloaded{self}')
            except:
                if debug_world_gen: print(f"{self} entered a never before loaded chunk and was destroyed")
            finally:
                self.kys()
        super().pre_update()