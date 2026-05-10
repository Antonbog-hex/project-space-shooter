import pygame
import gamestate as g
from base_classes import PhysicsObject,RotatingObject
from rendering import VisualObject
from spaceships import BaseEnemy , Spaceship
from physics import Explosion
from effects import TrailParticle
def init_textures():
    r = BaseBullet.radius
    BaseBullet.texture = pygame.Surface((2*r, 2*r), pygame.SRCALPHA)
    pygame.draw.circle(BaseBullet.texture, (214, 37, 28), (r, r), r)

    r = SniperBullet.radius
    SniperBullet.texture = pygame.Surface((2*r, 2*r), pygame.SRCALPHA)
    pygame.draw.circle(SniperBullet.texture, (212, 178, 53), (r, r), r)

    r = ShotgunPellet.radius
    ShotgunPellet.texture = pygame.Surface((2*r, 2*r), pygame.SRCALPHA)
    pygame.draw.circle(ShotgunPellet.texture, (48, 43, 186), (r, r), r)

    RocketBullet.texture = pygame.image.load('graphics/enemies/5.png')

class BaseBullet(PhysicsObject, VisualObject):
# Een kogel die het schip afvuurt.
    damage = 1
    speed = 700
    lifetime = 180
    radius = 4
    texture = None
    mass = 8
    def __init__(self, pos, vel, source, **kwargs):
        super().__init__(pos=pos, vel=vel, mass=self.__class__.mass, hitbox_radius=self.__class__.radius,image=self.__class__.texture,**kwargs)
        self._is_bullet = True
        self._is_rocket = False # used for debug
        self.source = source
        self.lifetime_ticker = self.__class__.lifetime   # frames it lives
    def check_collisions(self):
        for obj in g.active_object:
            if obj != self.source and self.hit(obj):
                if not obj._is_physics: continue
                if obj._is_planet:
                    self.kys()
                elif obj._is_target:
                    obj.kys()
                    self.kys()
                elif obj._is_enemy:
                    obj.take_damage(self.__class__.damage)
                    if self.source == g.player: obj.hit_by_player = True
                    self.kys()
                elif obj._is_player:
                    obj.take_damage(self.__class__.damage)
                    self.kys()
    def update(self):
        self.lifetime_ticker -= 1
        if self.lifetime_ticker <= 0:
            self.kys()
        self.check_collisions()
        super().update()
class SniperBullet(BaseBullet):
    damage = 3
    speed = 2800
    lifetime = 300
    radius = 5
    texture = None
    mass = 4
    def __init__(self, pos, vel, source, **kwargs):
        super().__init__(pos=pos, vel=vel, mass=self.__class__.mass, hitbox_radius=self.__class__.radius,image=self.__class__.texture,**kwargs)
class RocketBullet(BaseBullet,RotatingObject):
    damage = 2
    speed = 300
    lifetime = 900
    radius = 5
    texture = None
    explosion_duration = 45
    mass = 25
    snap_cutoff = 0.5
    to_moment_amplifier = 0.1
    moment_dampener = 0.05
    perp_correction_cutoff = 15
    min_approach_speed = 300
    def __init__(self,pos,vel,source):
        self.current_heading = source.current_heading
        angle = - self.current_heading.as_polar()[1]
        super().__init__(pos= pos,vel=vel,source=source , angle = angle)
        self._is_rocket = True
        self.base_image = self.base_image.convert_alpha()
        self.base_image = pygame.transform.rotozoom(self.base_image, -90, 0.025)
        self.image = self.base_image
        self.enemy_bullet = self.source._is_enemy
        if not self.enemy_bullet:
            self.target = min(g.enemies, key = lambda enemy: (enemy.pos - self.pos).magnitude_squared())
        else: self.target = g.player
    def turn_to(self,heading):
        BaseEnemy.turn_to(self, heading)
    def accelerate(self):
        self.acc += self.current_heading *  300
    def decelerate(self):
        pass
    def kys(self):
        g.active_object.add(Explosion(self.pos, self.__class__.radius * 3, self.__class__.explosion_duration))
        super().kys()
    def update(self):
        
        Spaceship._orientation_update(self)
        BaseEnemy.navigate_to_point(self, self.target.pos)
        g.particle_effects.add(TrailParticle(self.pos,radius = 4,color = (235, 125, 52)))
        super().update()
class ShotgunPellet(BaseBullet):
    damage = 1
    speed = 400
    lifetime = 120
    radius = 4
    texture = None
    mass = 4 
    def __init__(self, pos, vel, source, **kwargs):
        super().__init__(pos=pos, vel=vel, mass=self.__class__.mass, hitbox_radius=self.__class__.radius,image=self.__class__.texture,**kwargs)
init_textures()  
