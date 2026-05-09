import pygame
import random
import math
from constants import *
from base_classes import *
from physics import *
from effects import *
from bullets import *

class Spaceship(PhysicsObject,RotatingObject,VisualObject):
    pos_estim_step_size = 20# number of frames that get predicted per step
    max_hp = 1
    bullet_type = BaseBullet
    speed =  500
    bullet_reload = 30
    theme_colour = None
    standard_mass = 100
    max_shield = 0
    # Een ruimteschip: combineert physics, rotatie en een afbeelding. Berekent ook een voorspelde baan.
    def __init__(self, pos, vel, angle,image,hitbox_radius = None ,**kwargs):
        hitbox_radius = hitbox_radius or 15
        super().__init__(pos = pos,image = image ,vel = vel , mass = self.__class__.standard_mass, angle = angle , hitbox_radius= hitbox_radius, **kwargs)
        self.position_estimation = [self.pos for i in range(5)]
        self.hp = self.__class__.max_hp
        self.shield = self.__class__.max_shield
        self.shield_regen_ticker = 0
        self.bullet_ticker = self.__class__.bullet_reload
        self.current_heading = pygame.Vector2.from_polar((1, -self.angle)) # direction of pointing normvector
    def accelerate(self):
        self.acc = self.current_heading * self.speed + self.force / self.mass
        particle_effects.add(TrailParticle(self.pos - self.current_heading * self.hitbox_radius * 0.8 , color = self.__class__.theme_colour))
    def decelerate(self):
        self.acc =  - self.current_heading * self.speed * 0.5 + self.force / self.mass
        
    def pos_estimation_update(self,steps=5):
        # Simuleert de toekomstige baan door een kopie van het schip vooruit te bewegen zonder het echte schip aan te passen.
        active_object.remove(self)
        self.position_estimation.clear()
        tester = Predictor(pos = self.pos,vel= self.vel,force = self.force,mass=self.mass,hitbox_radius= self.hitbox_radius)
        for i in range(steps):
            for i in range (__class__.pos_estim_step_size):
                tester.pre_update()
                tester.update()
            self.position_estimation.append(tester.pos)
        
        active_object.add(self)
    def take_damage(self, amount=1):
        self.shield_regen_ticker = 750
        if self.shield > 0:
            self.shield -= amount
            amount = 0
            if self.shield < 0:
                amount = self.shield
                self.shield = 0
        self.hp -= amount
        if self.hp <= 0:
            if self._is_player:
                menu.active = True
                menu.is_death_screen = True
            active_object.add(Explosion(self.pos, self.hitbox_radius * 0.8, 60))
            self.kys()
    def heal(self,amount = 1):
        self.hp += amount
        self.hp = min(self.hp,self.__class__.max_hp)
        self.heal_animation()
    def shoot(self):
        if self.bullet_ticker > 0 : return
        bullet = self.__class__.bullet_type(self.pos,self.vel + self.current_heading * self.__class__.bullet_type.speed,self)
        bullets.add(bullet)      
        self.bullet_ticker = self.__class__.bullet_reload         
    def resolve_collisions(self):
        # Controleer of het schip een planeet raakt en stuit dan terug.
        for sprite in active_object:
            if not sprite._is_physics: continue
            if self.hit(sprite): # you cannot use id here because planets never check for collisions with spaceships
                if sprite._is_planet:
                    if sprite.style == 'black_hole': self.take_damage(self.hp)
                    self.elastic_collision(sprite,energy_dis= 1.1, damage_multiplier= 1)
                if sprite._is_spaceship:
                    self.elastic_collision(sprite, energy_dis = 1.4, damage_multiplier= 1)
    def shield_regen(self):
        if self.shield >= min(self.__class__.max_shield, self.hp): 
            return
        else:
            self.shield += 1
            self.shield_regen_ticker = 30
            self.shield_animation(30)
    def _orientation_update(self):
        self.current_heading = pygame.Vector2.from_polar((1, -self.angle))
    def update(self):
        if self.bullet_ticker > 0 : self.bullet_ticker -= 1
        if self.shield_regen_ticker > 0 : self.shield_regen_ticker -= 1
        else: self.shield_regen()
        self.angle_dampen()
        self.resolve_collisions()
        super().update()
    def pre_update(self):
        self._orientation_update()
        super().pre_update()
class BaseEnemy(Spaceship):
    # Dit is een basis vijand, alle andere vijanden erven hiervan
    # Verander deze waarden in de subklassen om een ander type vijand te maken
    spawn_weight = 1      # hoe groter, hoe vaker dit type spawnt - to be implemented
    bullet_type = BaseBullet
    bullet_reload = 180 # ticks to reload
    image_path = 'graphics/enemies/enemy_1.png' 
    hitbox_radius = 25
    max_hp = 3
    # turn_to parameters
    snap_cutoff = 1 # angle at wich it just snaps the turn
    to_moment_amplifier = 2 # how much the desired angle causes change in moment
    moment_dampener = 0.1 # dampening of the change in moment based on the magnitude of moment
    # navigate_to_point
    perp_correction_cutoff = 50 # perp vel at which correction starts
    min_approach_speed = 300
    #drift
    min_drift_speed = 350
    max_drift_speed = 400
    # avoid collision
    time_in_advance = 2 # number of seconds in advance checked for collision
    #swerve
    deflect_angle = 100 # the target deflection away from the line connecting ship and obstacle
    swerve_ticker_length = 45 # ticks the ship keeps flying away
    # check_visual (player finding)
    max_player_dist = 2500 # distance at which player if fully forgotten
    visual_cone_angle = 100 # degrees of visual cone
    player_max_memory = 900 # how many ticks the player is remembered for
    # get_pos_predict
    pred_iterations = 3
    # general movement
    orbit_force_req = 5000 # magnitude of force required to start orbitting
    planet_approach_req = 2000 # magnitude of force required to approach planet
    # player interact
    approach_dist = 500 # distance beyond which the enemy approaches
    max_rel_vel = 150 # maximum relative velocity before correcting
    pre_aim_ticks = 30 # ammount of ticks ahead of shooting the enemy starts to aim
    def __init__(self,pos,vel=0,angle=0,**kwargs):
        super().__init__(image = self.__class__.image_path, vel=vel, pos=pos, angle = angle,hitbox_radius = self.__class__.hitbox_radius , **kwargs)
        self.base_image = pygame.transform.rotozoom(self.base_image, -90, 0.04)
        self.image= self.base_image
        # movement
        self.strongest_grav = None # object that exerts strongest gravity (for orbiting)
        self.longer_target = None
        self.ticker = 0 # ticker for longer duretion movement eg. swerve, navigate_to
        self.longer_heading = None # for long duration swerve
        self.longer_target = None # for long duration navigate_to
        self.player_memory = 0 # ticker for remembering player 0 = forgotten
        self.desired_heading = None # this is for debug draw
        self.hit_by_player = False #  has it ever been hit by the player
        if debug_enemy:
            self.status= '' # string that states what enemies does this tick
            self.prev_satus = '' # string that states what enemies does prev tick 
            self.aim_target = None
    def turn_to(self,heading):
        turn_error = signed_angle_to( self.current_heading, heading)
        if abs(turn_error) < self.__class__.snap_cutoff: 
            self.angle += turn_error 
            self.angle_moment = 0
        else:
            self.angle_moment += turn_error * self.__class__.to_moment_amplifier - self.angle_moment * self.__class__.moment_dampener  # tune this multiplier         
    def navigate_to_point(self, point: pygame.Vector2, for_frames=1):
        # navigates to a certain point in world coord, for multible frames if desired
        if debug_enemy: self.status = 'navigating to a point'
        if point == self.pos: return
        if for_frames > 1:
            self.longer_target = point
            self.ticker = for_frames
        to_target = point - self.pos
        dist = to_target.magnitude()
        desired_heading = to_target / dist
        vel_perp = self.vel - desired_heading * self.vel.dot(desired_heading)
        perp_speed = vel_perp.magnitude()
        # tilt heading to oppose perpendicular drift if it gets large
        # this avoids out-of-control spinning
        if perp_speed > self.__class__.perp_correction_cutoff:
            correction = (-vel_perp.normalize()) * min(perp_speed / 300, 1.0) # magic numbers, self correcting behaviour
            desired_heading = (desired_heading + correction).normalize()
        self.desired_heading = desired_heading # for debug draw
        self.turn_to(desired_heading)
    
        # velocity component toward the target
        vel_toward = self.vel.dot(desired_heading)
        
        # braking distance: how far we travel before stopping at current speed
        # to prevent overshoot
        braking_acc = self.speed * 0.5  # matches decelerate()
        braking_dist = (vel_toward ** 2) / (2 * braking_acc) if vel_toward > 0 else 0
    
        aligned = self.current_heading *desired_heading > 0.7
    
        if braking_dist >= dist * 0.8:
            # close to overshoot, brake
            self.decelerate()
        elif vel_toward < self.__class__.min_approach_speed and aligned:
            self.accelerate()
    def drift(self):
        # basic movement if nothing is around
        if debug_enemy: self.status = 'drifting'
        self.turn_to(self.vel)
        if self.vel.magnitude_squared() > self.__class__.min_drift_speed **2:
            self.decelerate()
        elif self.vel.magnitude_squared() < self.__class__.max_drift_speed ** 2:
            self.accelerate()
    def orbit(self,object):
        # attempts to orbits the given object
        if  debug_enemy: self.status = 'orbiting'
        desired_cw = self.force.rotate(90) # a circular orbit should keep the force perpendicular
        desired_ccw = self.force.rotate(-90)
        rel_vel = self.vel - object.vel
        if rel_vel.x != 0 or rel_vel.y != 0:
            # this picks the heading most alligned with current velocity
            desired_heading = desired_cw if abs(signed_angle_to(rel_vel,desired_cw)) < abs(signed_angle_to(rel_vel,desired_ccw)) else desired_ccw
        else:
            desired_heading = desired_cw
        desired_heading = desired_heading.normalize()
        self.desired_heading = desired_heading
        grav_acc = self.force.magnitude() / self.mass
        r = (self.strongest_grav.pos - self.pos).magnitude()
        target_speed_sq =  1.2 * (grav_acc * r)
        speed_sq = ( self.vel*self.current_heading ) **2
        self.turn_to(desired_heading)
        if speed_sq < target_speed_sq :
            self.accelerate()
        if speed_sq > target_speed_sq :
           self.decelerate()
    def swerve(self,danger_object):
        if debug_enemy: self.status = 'swerving'
        delta = (danger_object.pos- self.pos).normalize()
        desired_cw = delta.rotate(self.__class__.deflect_angle)
        desired_ccw = delta.rotate(-self.__class__.deflect_angle)
        if self.current_heading * desired_cw >  self.current_heading * desired_ccw: #uses inproduct as a metric of alignedness
            desired_heading = desired_cw
        else:
            desired_heading = desired_ccw
        self.desired_heading = desired_heading
        self.longer_heading = desired_heading
        self.ticker = self.__class__.swerve_ticker_length
        self.turn_to(desired_heading)
        if self.current_heading * delta > 0:
            self.decelerate()
        else:
           self.accelerate()
    def avoid_collisions(self):

        predict_pos = self.next_pos(steps = self.__class__.time_in_advance / timestep) # from MovingObject

        linetest = LineHitbox(self.pos, predict_pos)
        swerving = False
        for planet in planets:
            if linetest.hit(planet):
                self.swerve(danger_object=planet)
                swerving = True
        return swerving      
    def check_visual(self):
        delta = player.pos - self.pos
        if delta.magnitude_squared() > self.__class__.max_player_dist**2: 
            self.player_memory = 0
            return False
        if delta.normalize() * self.current_heading < math.cos(self.__class__.visual_cone_angle/2): 
            return False
        linetest = LineHitbox(self.pos, player.pos)
        for planet in planets:
            if linetest.hit(planet):
                return False
        return True
    def resolve_ticker(self):
        if self.ticker == 0: return False
        if debug_enemy and self.ticker % 10 == 0:print(f'ticker {self.ticker}')
        self.ticker -= 1
        if self.longer_heading != None:
            self.turn_to(self.longer_heading)
            if self.current_heading * self.longer_heading > 0:
                self.accelerate()
            else:
               self.decelerate()
            if self.ticker == 0:
                self.longer_heading = None
        if self.longer_target != None:
            self.navigate_to_point(self.longer_target)
            if self.ticker == 0: self.longer_target = None
        return True
    def aim(self, pos):
        target_dir = (pos - self.pos)
        if target_dir.magnitude_squared() == 0:
            return False
        target_dir = target_dir.normalize()
        
        bullet_speed = self.__class__.bullet_type.speed
        perp_vel = self.vel - self.vel.dot(target_dir) * target_dir
        perp_speed = perp_vel.magnitude()
        
        if perp_speed >= bullet_speed:
            self.turn_to(target_dir)
            return False
        
        lead_angle = math.degrees(math.asin(perp_speed / bullet_speed))
        # rotate opposite to perp_vel to cancel it out
        sign = -1 if target_dir.rotate(90).dot(perp_vel) > 0 else 1
        corrected_dir = target_dir.rotate(sign * lead_angle)
        
        self.turn_to(corrected_dir)
        return corrected_dir.dot(self.current_heading) > 0.95  
    def get_pos_pred(self, target):
        bullet_speed = self.__class__.bullet_type.speed
    
        # start with current pos as initial guess
        predict = target.pos
    
        for _ in range(self.__class__.pred_iterations):
            target_vect = predict - self.pos
            dist = target_vect.magnitude()
            if dist == 0:
                return target.pos
            target_dir = target_vect / dist
    
            
            straight_speed = self.vel * target_dir
            perp_speed_sq = (self.vel - straight_speed * target_dir).magnitude_squared()
            bullet_speed_sq = bullet_speed ** 2
            effective_speed =  straight_speed + math.sqrt(bullet_speed_sq - perp_speed_sq) if bullet_speed_sq >= perp_speed_sq else straight_speed 
    
            if effective_speed <= 0:
                return target.pos
    
            travel_time = dist / effective_speed
            target_decimal_index = travel_time * fps / Spaceship.pos_estim_step_size
            delta = target_decimal_index - math.floor(target_decimal_index)
            floor_index = int(math.floor(target_decimal_index))
            ceil_index = floor_index + 1
            
            if target_decimal_index < 1.0:
                # between current pos and first dot
                predict = (1 - target_decimal_index) * target.pos + target_decimal_index * target.position_estimation[0]
            elif ceil_index > 4:
                predict = target.position_estimation[4]
            else:
                predict = (1 - delta) * target.position_estimation[floor_index - 1] + delta * target.position_estimation[floor_index]
    
        self.aim_target = predict
        return predict
    def match_vel(self,target):
        if debug_enemy: self.status = 'matching vel'
        d_vel = target.vel - self.vel
        if d_vel * self.current_heading > 0:
            self.accelerate()
        if d_vel * self.current_heading < 0:
            self.decelerate()
        if d_vel.magnitude_squared() >= self.__class__.max_rel_vel * 2: self.turn_to(target.pos-self.pos)   
    def pre_update(self):
        super().pre_update()
        if self.player_memory > 0:
            self.player_memory -= 1
        if self.check_visual():
            self.player_memory = self.__class__.player_max_memory
        self.general_movement()
        if debug_enemy:
            if self.status != self.prev_satus:
                print(self.status)
                self.prev_satus = self.status
    def general_movement(self):
        if self.avoid_collisions():
           return
        if self.resolve_ticker():
            return
        if self.player_memory > 0:
            self.player_interact()
            return
        if self.force.magnitude_squared() > self.__class__.orbit_force_req**2 and self.strongest_grav != None:
            self.orbit(self.strongest_grav)
            return
        if self.force.magnitude_squared() > self.__class__.planet_approach_req**2 and self.strongest_grav != None:
            if (self.vel - self.strongest_grav.vel) * (self.strongest_grav.pos - self.pos).normalize() < 250: # check if youre already approaching
                self.navigate_to_point(self.strongest_grav.pos)
                return
        self.drift()   
    def player_interact(self):
        if self.bullet_ticker < self.__class__.pre_aim_ticks:
            quality = self.aim(self.get_pos_pred(player))
            if self.bullet_ticker == 0 and quality: self.shoot()
            return
        if (self.pos - player.pos).magnitude_squared() > self.__class__.approach_dist ** 2: 
            self.navigate_to_point(player.pos)
        elif (self.vel - player.vel).magnitude_squared() > self.__class__.max_rel_vel ** 2:
            self.match_vel(player)
        else: self.turn_to(player.pos-self.pos) #self.aim(self.get_pos_pred(player))
    def kys(self):
        if self.hit_by_player: score_manager.add_score(self.__class__.score)
        super().kys()
class SimpleEnemy(BaseEnemy):
    theme_colour = (199, 59, 28)
    bullet_reload = 120
    spawn_weight = 4
    score = 30
    drop_chance = 0.1
    def kys(self):
        if random.uniform(0, 1) <= self.__class__.drop_chance:
            active_object.add(BasicGunItem(self.pos))
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
    theme_colour = (212, 178, 53)
    drop_chance = 0.6
    def kys(self):
        if random.uniform(0, 1) <= self.__class__.drop_chance:
            active_object.add(SniperGunItem(self.pos))
        super().kys()
    def back_up(self , player):
        player_vect = player.pos - self.pos
        if self.current_heading * player_vect < 0:
            self.accelerate()
        else: self.decelerate()
        self.turn_to(player_vect)
    def player_interact(self):
        if (self.pos - player.pos).magnitude_squared() < 600 ** 2:
            self.back_up(player)
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
    theme_colour = (28, 199, 193)
    def player_interact(self):
        self.navigate_to_point(player.pos)
        if (player.pos - self.pos).magnitude_squared() < (self.__class__.explosion_size * 0.9) ** 2:
            self.detonate()
    def detonate(self):
        active_object.add(Explosion(self.pos,duration = 120,radius = self.__class__.explosion_size))
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
    theme_colour = (48, 43, 186)
    drop_chance = 0.7
    def kys(self):
        if random.uniform(0, 1) <= self.__class__.drop_chance:
            active_object.add(ShotgunItem(self.pos))
        super().kys()
    def shoot(self):
        if self.bullet_ticker > 0 : return
        for i in range(8):
            aim = self.current_heading.rotate(random.uniform(-10, 10))
            bullet = self.__class__.bullet_type(self.pos,self.vel + aim * self.__class__.bullet_type.speed * random.uniform(0.5,1),self)
            bullets.add(bullet)      
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
    theme_colour = (196, 90, 20)
    drop_chance = 0.3
    def kys(self):
        if random.uniform(0, 1) <= self.__class__.drop_chance:
            active_object.add(RocketGunItem(self.pos))
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
    theme_colour = (40, 184, 107)
    drop_chance = 0.9
    def kys(self):
        if random.uniform(0, 1) <= self.__class__.drop_chance:
            active_object.add(HealItem(self.pos))
        super().kys()
    def __init__(self,pos,vel=0,angle=0,**kwargs):
        super().__init__(pos = pos, vel = vel, angle= angle, **kwargs)
        self.closest_ally = None
        self.enemy_mem_ticker = 0
        self.charge = 0
        self.last_animated_charge = 0
    def find_ally(self):
        enemies_local = enemies.copy()
        enemies_local.remove(self)
        if len(enemies) == 0: 
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
            for enemy in enemies:
                if (enemy.pos - self.pos).magnitude_squared() < self.__class__.heal_radius ** 2 :
                    enemy.heal()
        elif self.player_memory > 0:
            self.charge_up()
        self.enemy_mem_ticker -= 1
        super().update()
class Player(Spaceship):
    max_hp = 12
    grav_ticker = 1
    theme_colour = (53, 114, 212)
    speed = 750
    auto_score_ticks = 30
    max_shield = 5
    # De door de speler bestuurde ruimteschip. Leest toetsinvoer en past versnelling/rotatie aan.
    def __init__(self, pos, vel, angle):
        super().__init__(pos = pos, image = 'graphics/player/player.png',vel = vel, angle = angle, hitbox_radius= 20)
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
                bullets.add(bullet) 
        else:
            bullet = self.bullet_type(self.pos,self.vel + self.current_heading * self.bullet_type.speed,self)
            bullets.add(bullet)      
        self.bullet_ticker = self.bullet_reload 
    def update(self):
        if not debug_freecam: self.input_check()
        self.vel = self.vel.clamp_magnitude(self.__class__.speed)
        self.pos_estimation_update()
        if self.auto_score_ticker <= 0:
            score_manager.add_score(1)
            self.auto_score_ticker = self.__class__.auto_score_ticks
        else:
            self.auto_score_ticker -= 1
        super().update()     

# Lijst van alle vijandtypes — voeg hier nieuwe types toe als je ze maakt
all_enemy_types = [ SimpleEnemy, SniperEnemy,SuicideEnemy,ShotgunEnemy,RocketEnemy,HealingEnemy] 