import pygame
from constants import *
from base_classes import *
from physics import *
from spaceships import *

class Item(PhysicsObject,VisualObject):
    background_colour = (255,255,255)
    border_size = 3
    def __init__(self,pos,foreground_image,**kwargs):
        w,h = foreground_image.get_size()
        background = pygame.Surface((w + 2* self.__class__.border_size,h + 2* self.__class__.border_size),pygame.SRCALPHA)
        cx, cy = background.get_size()
        cx, cy = cx//2, cy//2
        radius = max(h,w)//2
        pygame.draw.circle(background, (*self.__class__.background_colour, 200), (cx,cy), radius + self.__class__.border_size)
        pygame.draw.circle(background, (*self.__class__.background_colour, 150), (cx,cy), radius)
        
        background.blit(foreground_image,(self.__class__.border_size,self.__class__.border_size))
        super().__init__(pos,image= background,mass = 20,hitbox_radius = radius + 3,**kwargs)
    def check_collision(self):
        for sprite in active_object:
            if not sprite._is_physics: continue
            if self.hit(sprite): 
                if sprite._is_planet:
                    if sprite.style == 'black_hole': self.kys()
                    self.elastic_collision(sprite,energy_dis= 1.8)
                if sprite._is_spaceship:
                    if sprite._is_player: self.pickup(player)
                    self.elastic_collision(sprite, energy_dis = 0.5)
    def pickup(self,pickup):
        pass
    def update(self):
        self.check_collision()
        super().update()
class HealItem(Item):
    image_path = 'graphics/enemies/6.png'
    background_colour = HealingEnemy.theme_colour
    def __init__(self,pos,**kwargs):
         foreground_image = pygame.image.load(self.__class__.image_path)
         foreground_image = foreground_image.convert_alpha()
         foreground_image = pygame.transform.rotozoom(foreground_image, 0, 0.025)
         super().__init__(pos,foreground_image,**kwargs)
    def pickup(self,player):
        if player.hp != player.__class__.max_hp:
            player.heal(8)
        else:
            score_manager.add_score(50)
        self.kys()
class GunItem(Item):
    background_colour = RocketEnemy.theme_colour
    name = 'Rocket'
    image_path = 'graphics/enemies/5.png'
    def __init__(self,pos,**kwargs):
        foreground_image = pygame.image.load(self.__class__.image_path)
        foreground_image = foreground_image.convert_alpha()
        foreground_image = pygame.transform.rotozoom(foreground_image, 0, 0.025)
        super().__init__(pos,foreground_image,**kwargs)
    def pickup(self,ship):
        if ship.current_gun == self.__class__.name:
            score_manager.add_score(20)
        else:
            ship.current_gun = self.__class__.name
            ship._bullettype_update()
        self.kys()
class RocketGunItem(GunItem):
    pass
class ShotgunItem(GunItem):
    background_colour = ShotgunEnemy.theme_colour
    name = 'Shotgun'
    image_path = 'graphics/enemies/Enemy_2.png'
class BasicGunItem(GunItem):
    background_colour = SimpleEnemy.theme_colour
    name = 'Basic'
    image_path = 'graphics/enemies/Enemy_1.png'
class SniperGunItem(GunItem):
    background_colour = SniperEnemy.theme_colour
    name = 'Sniper'
    image_path = 'graphics/enemies/Enemy_3.png'