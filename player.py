import pygame
import random
import gamestate as g
from space_shooter import Spaceship
from constants import player_theme_colour, debug_freecam
from bullets import ShotgunPellet,BaseBullet,SniperBullet,RocketBullet
class Player(Spaceship):
    max_hp = 12
    grav_ticker = 1
    theme_colour = player_theme_colour
    speed = 750
    auto_score_ticks = 30
    max_shield = 5
    # De door de speler bestuurde ruimteschip. Leest toetsinvoer en past versnelling/rotatie aan.
    def __init__(self, pos, vel, angle):
        super().__init__(pos = pos, image = 'graphics/player/player.png',vel = vel, angle = angle, hitbox_radius= 20)
        self._is_player = True
        self.base_image = pygame.transform.rotozoom(self.base_image, -90, 0.04)
        self.image = self.base_image
        self.auto_score_ticker = self.__class__.auto_score_ticks
        self.current_gun = 'Basic'
        self._bullettype_update()
    def _bullettype_update(self):
        if self.current_gun == 'Rocket':
            self.bullet_reload = 250
            self.bullet_type = RocketBullet
        elif self.current_gun == 'Sniper':
            self.bullet_reload = 40
            self.bullet_type = SniperBullet
        elif self.current_gun == 'Shotgun':
            self.bullet_reload = 100
            self.bullet_type = ShotgunPellet
        else:
            self.bullet_reload = 30
            self.bullet_type = BaseBullet
            
    def input_check(self):
        # Verwerkt toetsinvoer: pijl omhoog = gas, links/rechts = draaien
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.accelerate()       
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.angle_moment += 20
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.angle_moment += -20
        if keys[pygame.K_SPACE]:
            self.shoot()
    def shoot(self):
        if self.bullet_ticker > 0 : return
        if self.current_gun == 'Shotgun':
            for i in range(8):
                aim = self.current_heading.rotate(random.uniform(-10, 10))
                bullet = self.bullet_type(self.pos,self.vel + aim * self.__class__.bullet_type.speed * random.uniform(0.5,1),self)
                g.bullets.add(bullet) 
        else:
            bullet = self.bullet_type(self.pos,self.vel + self.current_heading * self.bullet_type.speed,self)
            g.bullets.add(bullet)      
        self.bullet_ticker = self.bullet_reload 
    def update(self):
        if not debug_freecam: self.input_check()
        self.vel = self.vel.clamp_magnitude(self.__class__.speed)
        self.pos_estimation_update()
        if self.auto_score_ticker <= 0:
            g.score_manager.add_score(1)
            self.auto_score_ticker = self.__class__.auto_score_ticks
        else:
            self.auto_score_ticker -= 1
        super().update()     

