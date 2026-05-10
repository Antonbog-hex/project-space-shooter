import pygame
import gamestate as g
import math
from base_classes import PhysicsObject, RotatingObject,LineHitbox
from rendering import VisualObject
from physics import Predictor, Explosion
from effects import TrailParticle
from constants import fps,timestep,debug_enemy

def signed_angle_to(v1, v2):
    cross = -(v1.x * v2.y - v1.y * v2.x)
    dot = v1.dot(v2)
    return math.degrees(math.atan2(cross, dot))

class Spaceship(PhysicsObject,RotatingObject,VisualObject):
    pos_estim_step_size = 20# number of frames that get predicted per step
    max_hp = 1
    bullet_type = None
    speed =  500
    bullet_reload = 30
    theme_colour = None
    standard_mass = 100
    max_shield = 0
    # Een ruimteschip: combineert physics, rotatie en een afbeelding. Berekent ook een voorspelde baan.
    def __init__(self, pos, vel, angle,image,hitbox_radius = None ,**kwargs):
        hitbox_radius = hitbox_radius or 15
        super().__init__(pos = pos,image = image ,vel = vel , mass = self.__class__.standard_mass, angle = angle , hitbox_radius= hitbox_radius, **kwargs)
        self._is_spaceship = True
        self.position_estimation = [self.pos for i in range(5)]
        self.hp = self.__class__.max_hp
        self.shield = self.__class__.max_shield
        self.shield_regen_ticker = 0
        self.bullet_ticker = self.__class__.bullet_reload
        self.current_heading = pygame.Vector2.from_polar((1, -self.angle)) # direction of pointing normvector
    def accelerate(self):
        self.acc = self.current_heading * self.speed + self.force / self.mass
        g.particle_effects.add(TrailParticle(self.pos - self.current_heading * self.hitbox_radius * 0.8 , color = self.__class__.theme_colour))
    def decelerate(self):
        self.acc =  - self.current_heading * self.speed * 0.5 + self.force / self.mass
        
    def pos_estimation_update(self,steps=5):
        # Simuleert de toekomstige baan door een kopie van het schip vooruit te bewegen zonder het echte schip aan te passen.
        
        self.position_estimation.clear()
        tester = Predictor(pos = self.pos,vel= self.vel,force = self.force,mass=self.mass,hitbox_radius= self.hitbox_radius, source= self)
        for i in range(steps):
            for i in range (__class__.pos_estim_step_size):
                tester.pre_update()
                tester.update()
            self.position_estimation.append(tester.pos)
        
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
                g.menu.active = True
                g.menu.is_death_screen = True
            g.active_object.add(Explosion(self.pos, self.hitbox_radius * 0.8, 60))
            self.kys()
    def heal(self,amount = 1):
        self.hp += amount
        self.hp = min(self.hp,self.__class__.max_hp)
        self.heal_animation()
    def shoot(self):
        if self.bullet_ticker > 0 : return
        bullet = self.__class__.bullet_type(pos = self.pos,vel= (self.vel + self.current_heading * self.__class__.bullet_type.speed),source = self)
        g.bullets.add(bullet)      
        self.bullet_ticker = self.__class__.bullet_reload         
    def resolve_collisions(self):
        # Controleer of het schip een planeet raakt en stuit dan terug.
        for sprite in g.active_object:
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
    bullet_type = None
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
        self._is_enemy = True
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
        for planet in g.planets:
            if linetest.hit(planet):
                self.swerve(danger_object=planet)
                swerving = True
        return swerving      
    def check_visual(self):
        delta = g.player.pos - self.pos
        if delta.magnitude_squared() > self.__class__.max_player_dist**2: 
            self.player_memory = 0
            return False
        if delta.normalize() * self.current_heading < math.cos(self.__class__.visual_cone_angle/2): 
            return False
        linetest = LineHitbox(self.pos, g.player.pos)
        for planet in g.planets:
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
            quality = self.aim(self.get_pos_pred(g.player))
            if self.bullet_ticker == 0 and quality: self.shoot()
            return
        if (self.pos - g.player.pos).magnitude_squared() > self.__class__.approach_dist ** 2: 
            self.navigate_to_point(g.player.pos)
        elif (self.vel - g.player.vel).magnitude_squared() > self.__class__.max_rel_vel ** 2:
            self.match_vel(g.player)
        else: self.turn_to(g.player.pos-self.pos) #self.aim(self.get_pos_pred(player))
    def kys(self):
        if self.hit_by_player: g.score_manager.add_score(self.__class__.score)
        super().kys()
