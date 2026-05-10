import pygame
import constants as g
from base_classes import PhysicsObject,GravityObject
from rendering import VisualObject
from base_classes import CircularHitbox
from effects import ExplosionEffect
class Predictor(PhysicsObject):
    grav_ticker = 1
    def pre_update(self):
        GravityObject.pre_update(self)
    
    def update(self):
        for obj in g.active_object:
            if self.hit(obj) and obj._is_physics and obj._is_item:
                self.elastic_collision(obj,energy_dis=1.1,reflective=False)
        super().update()
class Explosion(CircularHitbox):
    damage = 3
    def __init__(self,pos,radius,duration):
        self.duration = duration
        super().__init__(pos=pos,radius  = radius)
        self.hit_list = []
        g.particle_effects.add(ExplosionEffect(self.pos,self.hitbox_radius,self.duration))
    def update(self):
        for element in g.enemies + [g.player]:
            if (not element in self.hit_list) and self.hit(element):
                self.hit_list.append(element)
                element.take_damage(self.__class__.damage)
                element.vel += 1000 * (element.pos - self.pos) / element.mass
        self.duration -= 1
        if self.duration <= 0: self.kys()
class DebugMass(PhysicsObject,VisualObject):
    def __init__(self):
        image = pygame.Surface((20,20))
        pygame.draw.circle(image,'red',(10,10),10)
        super().__init__((50,50),mass = 300,image=image .convert_alpha())
    def update(self):
        if pygame.mouse.get_pressed()[0]:
            self.mass = 1000
            mouse_screen = pygame.Vector2(pygame.mouse.get_pos())
            mouse_pre = mouse_screen / g.camera.scaler
            mouse_world = mouse_pre - g.camera.offset + g.camera.pos
            self.pos = mouse_world
            self.vel = pygame.Vector2(0)
        else:
            self.mass = 0.01
            self.vel = pygame.Vector2(0)
        super().update()

