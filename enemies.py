import random
import gamestate as g
from spaceships import BaseEnemy
from items import BasicGunItem, SniperGunItem, ShotgunItem, RocketGunItem, HealItem
from constants import (simple_theme_colour,sniper_theme_colour,suicide_theme_colour,
                       shotgun_theme_colour,rocket_theme_colour,healer_theme_colour)
from bullets import SniperBullet, ShotgunPellet, RocketBullet
from physics import Explosion
class SimpleEnemy(BaseEnemy):
    theme_colour = simple_theme_colour
    bullet_reload = 120
    spawn_weight = 4
    score = 30
    drop_chance = 0.1
    def kys(self):
        if random.uniform(0, 1) <= self.__class__.drop_chance:
            g.active_object.add(BasicGunItem(self.pos))
        super().kys()
class SniperEnemy(BaseEnemy):
    score  = 50
    spawn_weight = 3
    bullet_reload = 200 # ticks to reload
    image_path = 'graphics/enemies/enemy_3.png' 
    hitbox_radius = 25
    max_hp = 2
    # navigate_to_point
    perp_correction_cutoff = 100 # perp vel at which correction starts
    # check_visual (player finding)
    max_player_dist = 3500 # distance at which player if fully forgotten
    # player interact
    approach_dist = 1200 # distance beyond which the enemy approaches
    max_rel_vel = 500 # maximum relative velocity before correcting
    pre_aim_ticks = 50 # ammount of ticks ahead of shooting the enemy starts to aim 
    speed = 350
    bullet_type = SniperBullet
    theme_colour = sniper_theme_colour
    drop_chance = 0.6
    def kys(self):
        if random.uniform(0, 1) <= self.__class__.drop_chance:
            g.active_object.add(SniperGunItem(self.pos))
        super().kys()
    def back_up(self , player):
        player_vect = player.pos - self.pos
        if self.current_heading * player_vect < 0:
            self.accelerate()
        else: self.decelerate()
        self.turn_to(player_vect)
    def player_interact(self):
        if (self.pos - g.player.pos).magnitude_squared() < 600 ** 2:
            self.back_up(g.player)
        super().player_interact()
class SuicideEnemy(BaseEnemy):
    score  = 60
    spawn_weight = 2
    bullet_reload = 180 # ticks to reload
    image_path = 'graphics/enemies/enemy_4.png' 
    hitbox_radius = 25
    max_hp = 2
    explosion_size = 120
    # navigate_to_point
    min_approach_speed = 500
    # check_visual (player finding)
    visual_cone_angle = 90 # degrees of visual cone
    theme_colour = suicide_theme_colour
    def player_interact(self):
        self.navigate_to_point(g.player.pos)
        if (g.player.pos - self.pos).magnitude_squared() < (self.__class__.explosion_size * 0.9) ** 2:
            self.detonate()
    def detonate(self):
        g.active_object.add(Explosion(self.pos,duration = 120,radius = self.__class__.explosion_size))
        self.kys()
class ShotgunEnemy(BaseEnemy):
    score = 80
    spawn_weight = 2   
    bullet_type = ShotgunPellet
    image_path = 'graphics/enemies/enemy_2.png' 
    max_hp = 4
    min_approach_speed = 350
    visual_cone_angle = 110 # degrees of visual cone
    approach_dist = 400 # distance beyond which the enemy approaches
    max_rel_vel = 100 # maximum relative velocity before correcting
    theme_colour = shotgun_theme_colour
    drop_chance = 0.7
    def kys(self):
        if random.uniform(0, 1) <= self.__class__.drop_chance:
            g.active_object.add(ShotgunItem(self.pos))
        super().kys()
    def shoot(self):
        if self.bullet_ticker > 0 : return
        for i in range(8):
            aim = self.current_heading.rotate(random.uniform(-10, 10))
            bullet = self.__class__.bullet_type(self.pos,self.vel + aim * self.__class__.bullet_type.speed * random.uniform(0.5,1),self)
            g.bullets.add(bullet)      
        self.bullet_ticker = self.__class__.bullet_reload  
class RocketEnemy(BaseEnemy):
    score = 140
    spawn_weight = 1      # hoe groter, hoe vaker dit type spawnt
    bullet_reload = 300 # ticks to reload
    image_path = 'graphics/enemies/7.png' 
    hitbox_radius = 30
    max_hp = 3
    # navigate_to_point
    perp_correction_cutoff = 100 # perp vel at which correction starts
    # check_visual (player finding)
    max_player_dist = 3500 # distance at which player if fully forgotten
    # player interact
    approach_dist = 1200 # distance beyond which the enemy approaches
    max_rel_vel = 500 # maximum relative velocity before correcting
    pre_aim_ticks = 50 # ammount of ticks ahead of shooting the enemy starts to aim 
    speed = 350
    bullet_type = RocketBullet
    theme_colour = rocket_theme_colour
    drop_chance = 0.3
    def kys(self):
        if random.uniform(0, 1) <= self.__class__.drop_chance:
            g.active_object.add(RocketGunItem(self.pos))
        super().kys()
class HealingEnemy(BaseEnemy):
    spawn_weight = 1      # hoe groter, hoe vaker dit type spawnt - to be implemented
    score  = 100
    image_path = 'graphics/enemies/6.png' 
    hitbox_radius = 25
    max_hp = 3

    # avoid collision
    time_in_advance = 3 # number of seconds in advance checked for collision
    #swerve
    swerve_ticker_length = 75 # ticks the ship keeps flying away
    # check_visual (player finding)
    max_player_dist = 3000 # distance at which player if fully forgotten
    visual_cone_angle = 100 # degrees of visual cone
    player_max_memory = 2000 # how many ticks the player is remembered for
    
    charge_up_length = 480
    heal_radius = 500
    theme_colour = healer_theme_colour
    drop_chance = 0.9
    def kys(self):
        if random.uniform(0, 1) <= self.__class__.drop_chance:
            g.active_object.add(HealItem(self.pos))
        super().kys()
    def __init__(self,pos,vel=0,angle=0,**kwargs):
        super().__init__(pos = pos, vel = vel, angle= angle, **kwargs)
        self.closest_ally = None
        self.enemy_mem_ticker = 0
        self.charge = 0
        self.last_animated_charge = 0
    def find_ally(self):
        enemies_local = g.enemies.copy()
        enemies_local.remove(self)
        if len(g.enemies) == 0: 
            ally = None
        else:
            ally = min(enemies_local,key= lambda enemy: (enemy.pos - self.pos).magnitude_squared())
        self.closest_ally = ally
        self.enemy_mem_ticker = 600
    def charge_up(self):
        self.charge += 1
        if self.charge > self.last_animated_charge:
            length = min(max(int((self.__class__.charge_up_length-self.charge )*0.25),15), 60)
            self.charge_up_animation(length)
            self.last_animated_charge += length
        
    def player_interact(self):
        if self.enemy_mem_ticker <= 0: self.find_ally() 
        if self.closest_ally != None: self.navigate_to_point(self.closest_ally.pos)
    def update(self):
        if self.charge >= self.__class__.charge_up_length:
            self.charge = 0
            self.last_animated_charge = 0
            for enemy in g.enemies:
                if (enemy.pos - self.pos).magnitude_squared() < self.__class__.heal_radius ** 2 :
                    enemy.heal()
        elif self.player_memory > 0:
            self.charge_up()
        self.enemy_mem_ticker -= 1
        super().update()
# Lijst van alle vijandtypes — voeg hier nieuwe types toe als je ze maakt
all_enemy_types = [ SimpleEnemy, SniperEnemy,SuicideEnemy,ShotgunEnemy,RocketEnemy,HealingEnemy] 