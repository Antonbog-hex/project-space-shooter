import pygame
from constants import *
from base_classes import *
from physics import *

class ParticleEffect(VisualObject):
    image = None
    def __init__(self, pos,duration = 10):
        super().__init__(pos = pos, image= self.__class__.image)
        self.ticker = duration
        super().update()
    def update_image(self):
        pass        
    def update(self):
        self.update_image()
        self.ticker -= 1
        if self.ticker <= 0: self.kys()
class ExplosionEffect(ParticleEffect):
    def __init__(self, pos, radius=30, duration = 60):
        self.radius = radius
        self.duration = duration
        super().__init__(pos=pos,duration = duration)
    
    def update_image(self):
        progress = 1 - (self.ticker / self.duration)  # 0 to 1
        current_radius = int(self.radius * (1 + progress * 2))
        alpha = int(255 * (1 - progress))
        red = 255
        green = int(200 * (1 - progress))
        
        size = current_radius * 2
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (red, green, 0, alpha), (current_radius, current_radius), current_radius)
class TrailParticle(ParticleEffect):
    duration = 20
    
    def __init__(self, pos, radius=6, color=(255, 140, 0)):
        self.radius = radius
        self.color = color
        super().__init__(pos=pos, duration=self.__class__.duration)
    
    def update_image(self):
        if not hasattr(self, 'radius'): return
        progress = 1 - (self.ticker / self.__class__.duration)
        alpha = int(255 * (1 - progress))
        current_radius = max(1, int(self.radius * (1 - progress * 0.7)))
        
        size = current_radius * 2
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (*self.color, alpha), (current_radius, current_radius), current_radius)   
class Explosion(CircularHitbox):
    damage = 3
    def __init__(self,pos,radius,duration):
        self.duration = duration
        super().__init__(pos=pos,radius  = radius)
        self.hit_list = []
        particle_effects.add(ExplosionEffect(self.pos,self.hitbox_radius,self.duration))
    def update(self):
        for element in enemies + [player]:
            if (not element in self.hit_list) and self.hit(element):
                self.hit_list.append(element)
                element.take_damage(self.__class__.damage)
                element.vel += 1000 * (element.pos - self.pos) / element.mass
        self.duration -= 1
        if self.duration <= 0: self.kys()

