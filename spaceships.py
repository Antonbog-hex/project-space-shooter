import pygame
import gamestate as g
import math
from base_classes import PhysicsObject, RotatingObject,LineHitbox
from rendering import VisualObject
from other_objects import Predictor, Explosion
from effects import TrailParticle
from constants import fps,timestep,debug_enemy

def signed_angle_to(v1, v2):
    # Berekent de hoek van v1 naar v2 in graden, met teken (+ = linksom, - = rechtsom)
    cross = -(v1.x * v2.y - v1.y * v2.x)
    dot = v1.dot(v2)
    return math.degrees(math.atan2(cross, dot))

class Spaceship(PhysicsObject,RotatingObject,VisualObject):
    # Een ruimteschip: combineert physics, rotatie en een afbeelding. Berekent ook een voorspelde baan.
    pos_estim_step_size = 20 # aantal frames dat per stap vooruitgesimuleerd wordt
    max_hp = 1
    bullet_type = None
    speed = 500
    bullet_reload = 30 # aantal frames tussen schoten
    theme_colour = None
    standard_mass = 100
    max_shield = 0

    def __init__(self, pos, vel, angle,image,hitbox_radius = None ,**kwargs):
        hitbox_radius = hitbox_radius or 15
        super().__init__(pos = pos,image = image ,vel = vel , mass = self.__class__.standard_mass, angle = angle , hitbox_radius= hitbox_radius, **kwargs)
        self._is_spaceship = True
        self.position_estimation = [self.pos for i in range(5)]  # Lijst van voorspelde toekomstige posities
        self.hp = self.__class__.max_hp
        self.shield = self.__class__.max_shield
        self.shield_ticker = 0      # Teller voor vertraging voor schildregeneratie
        self.bullet_ticker = self.__class__.bullet_reload
        # Eenheidsvector die aangeeft in welke richting het schip wijst
        self.current_heading = pygame.Vector2.from_polar((1, -self.angle))

    def accelerate(self):
        # Versnelt in de richting van de huidige koers en voegt een trail toe
        self.acc = self.current_heading * self.speed + self.force / self.mass
        g.particle_effects.add(TrailParticle(self.pos - self.current_heading * self.hitbox_radius * 0.8 , color = self.__class__.theme_colour))

    def decelerate(self):
        # Remt door tegen de huidige koers in te versnellen (halve stuwkracht)
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
        # Reset de schildregeneratietimer
        self.shield_regenticker = 750
        if self.shield > 0:
            # Schild absorbeert schade eerst; overgebleven schade gaat naar HP
            self.shield -= amount
            amount = 0
            if self.shield < 0:
                amount = self.shield
                self.shield = 0
        self.hp -= amount
        if self.hp <= 0:
            if self._is_player:
                # Speler dood: toon doodscherm
                g.menu.active = True
                g.menu.is_death_screen = True
            g.active_object.add(Explosion(self.pos, self.hitbox_radius * 0.8, 60))
            self.kys()

    def heal(self,amount = 1):
        # Herstel HP zonder het maximum te overschrijden
        self.hp += amount
        self.hp = min(self.hp,self.__class__.max_hp)
        self.heal_animation()

    def shoot(self):
        # Vuur een kogel af als de herlaadtimer op nul staat
        if self.bullet_ticker > 0 : return
        # Kogel erft de snelheid van het schip plus de eigen snelheid
        bullet = self.__class__.bullet_type(pos = self.pos,vel= (self.vel + self.current_heading * self.__class__.bullet_type.speed),source = self)
        g.bullets.add(bullet)      
        self.bullet_ticker = self.__class__.bullet_reload         

    def resolve_collisions(self):
        # Controleer of het schip een planeet raakt en stuit dan terug.
        for sprite in g.active_object:
            if not sprite._is_physics: continue
            if self.hit(sprite): # you cannot use id here because planets never check for collisions with spaceships
                if sprite._is_planet:
                    # Zwarte gaten doden direct; andere planeten stoten terug met extra energie
                    if sprite.style == 'black_hole': self.take_damage(self.hp)
                    self.elastic_collision(sprite,energy_dis= 1.1, damage_multiplier= 1)
                if sprite._is_spaceship:
                    self.elastic_collision(sprite, energy_dis = 1.4, damage_multiplier= 1)

    def shield_regen(self):
        # Regenereer het schild als het nog niet vol is
        if self.shield >= min(self.__class__.max_shield, self.hp):
            self.shield_animation(60)
            self.shield_ticker = max(self.shield_ticker , 300)
            return
        else:
            self.shield += 1
            self.shield_ticker = 30
            self.shield_animation(30)

    def _orientation_update(self):
        self.current_heading = pygame.Vector2.from_polar((1, -self.angle))

    def update(self):
        if self.bullet_ticker > 0 : self.bullet_ticker -= 1
        if self.shield_ticker > 0 : self.shield_ticker -= 1
        else: self.shield_regen()   # Begin schildregeneratie als de timer op nul staat
        self.angle_dampen()
        self.resolve_collisions()
        super().update()

    def pre_update(self):
        self._orientation_update()
        super().pre_update()


class BaseEnemy(Spaceship):
    # Dit is een basis vijand, alle andere vijanden erven hiervan
    # Verander deze waarden in de subklassen om een ander type vijand te maken
    spawn_weight = 1            # hoe groter, hoe vaker dit type spawnt
    bullet_type = None
    bullet_reload = 180
    image_path = 'graphics/enemies/enemy_1.png' 
    hitbox_radius = 25
    max_hp = 3

    # turn_to parameters
    snap_cutoff = 1
    to_moment_amplifier = 2     # hoe sterk de gewenste hoekfout het draaimoment beïnvloedt
    moment_dampener = 0.1       # demping van het draaimoment om oscillatie te voorkomen

    # navigate_to_point
    perp_correction_cutoff = 50 # zijdelingse snelheid (px/s) waarbij koerscorrectie begint
    min_approach_speed = 300    # minimumsnelheid bij benadering van een doel

    # drift
    min_drift_speed = 350
    max_drift_speed = 400

    # avoid collision
    time_in_advance = 2         # aantal seconden vooruit dat op botsingen gecheckt wordt

    # swerve
    deflect_angle = 100         # uitwijkhoek ten opzichte van de lijn naar het obstakel
    swerve_ticker_length = 45   # frames dat het schip wegvliegt na een uitwijkmanoeuvre

    # check_visual (speler vinden)
    max_player_dist = 2500      # afstand waarop de speler volledig vergeten wordt
    visual_cone_angle = 100     # breedte van de gezichtskegel in graden
    player_max_memory = 900     # frames dat de speler onthouden wordt na het verdwijnen

    # get_pos_pred
    pred_iterations = 3         # aantal iteraties voor de positievoorspelling

    # general movement
    orbit_force_req = 5000      # minimale zwaartekracht (magnitude) om te beginnen met cirkelen
    planet_approach_req = 2000  # minimale zwaartekracht om een planeet te benaderen

    # player interact
    approach_dist = 500         # afstand waarbuiten de vijand de speler actief benadert
    max_rel_vel = 150           # maximale relatieve snelheid voordat de vijand bijstuurt
    pre_aim_ticks = 30          # frames voor het schieten dat de vijand begint te mikken

    def __init__(self,pos,vel=0,angle=0,**kwargs):
        super().__init__(image = self.__class__.image_path, vel=vel, pos=pos, angle = angle,hitbox_radius = self.__class__.hitbox_radius , **kwargs)
        self.base_image = pygame.transform.rotozoom(self.base_image, -90, 0.04)
        self.image= self.base_image
        self._is_enemy = True

        # Bewegingsstatus
        self.strongest_grav = None    # object dat de sterkste zwaartekracht uitoefent (voor cirkelen)
        self.longer_target = None     # doelpunt voor een langdurige navigatieopdracht
        self.ticker = 0               # teller voor langdurige acties zoals swerven of navigeren
        self.longer_heading = None    # gewenste koers tijdens een langdurige swerve
        self.longer_target = None     # doelpunt voor een langdurige navigate_to
        self.player_memory = 0        # teller voor het onthouden van de speler; 0 = vergeten
        self.desired_heading = None   # gewenste koers (voor debugtekening)
        self.hit_by_player = False    # ooit geraakt door de speler (voor scoreberekening)

        if debug_enemy:
            self.status= ''           # huidige actie als tekst (voor debugprint)
            self.prev_satus = ''      
            self.aim_target = None    # voorspeld mikpunt (voor debugtekeningen)

    def turn_to(self,heading):
        # Draai het schip naar de gewenste koers via het draaimoment
        turn_error = signed_angle_to( self.current_heading, heading)
        if abs(turn_error) < self.__class__.snap_cutoff: 
            self.angle += turn_error 
            self.angle_moment = 0
        else:
            self.angle_moment += turn_error * self.__class__.to_moment_amplifier - self.angle_moment * self.__class__.moment_dampener

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

        # Bereken de zijdelingse snelheidscomponent (loodrecht op de koers)
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
    
        # Controleer of het schip al voldoende op de gewenste koers gericht is
        aligned = self.current_heading * desired_heading > 0.7
    
        if braking_dist >= dist * 0.8:
            # Te dicht bij overschieten: rem af
            self.decelerate()
        elif vel_toward < self.__class__.min_approach_speed and aligned:
            # Nog niet snel genoeg en goed gericht: versnellen
            self.accelerate()

    def drift(self):
        # basic movement if nothing is around
        if debug_enemy: self.status = 'drifting'
        self.turn_to(self.vel)  # Wijs in de richting van de huidige beweging
        if self.vel.magnitude_squared() > self.__class__.min_drift_speed **2:
            self.decelerate()
        elif self.vel.magnitude_squared() < self.__class__.max_drift_speed ** 2:
            self.accelerate()

    def orbit(self,object):
        # attempts to orbits the given object
        if  debug_enemy: self.status = 'orbiting'
        # Een cirkelbaan vereist dat de zwaartekracht loodrecht staat op de snelheid
        desired_cw = self.force.rotate(90)    # kloksgewijs
        desired_ccw = self.force.rotate(-90)  # tegen de klok in
        rel_vel = self.vel - object.vel
        if rel_vel.x != 0 or rel_vel.y != 0:
            # Kies de richting die het meest overeenkomt met de huidige snelheid
            desired_heading = desired_cw if abs(signed_angle_to(rel_vel,desired_cw)) < abs(signed_angle_to(rel_vel,desired_ccw)) else desired_ccw
        else:
            desired_heading = desired_cw
        desired_heading = desired_heading.normalize()
        self.desired_heading = desired_heading

        # Bereken de ideale baansnelheid: v² = g * r (cirkelbaan)
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
        # Wijk uit voor een obstakel door er haaks langs te vliegen
        if debug_enemy: self.status = 'swerving'
        delta = (danger_object.pos- self.pos).normalize()
        desired_cw = delta.rotate(self.__class__.deflect_angle)
        desired_ccw = delta.rotate(-self.__class__.deflect_angle)
        # Kies de uitwijkrichting die het meest overeenkomt met de huidige koers
        if self.current_heading * desired_cw >  self.current_heading * desired_ccw:
            desired_heading = desired_cw
        else:
            desired_heading = desired_ccw
        self.desired_heading = desired_heading
        # Sla de swerve op voor meerdere frames via de ticker
        self.longer_heading = desired_heading
        self.ticker = self.__class__.swerve_ticker_length
        self.turn_to(desired_heading)
        if self.current_heading * delta > 0:
            # Schip vliegt nog naar het obstakel toe: rem af
            self.decelerate()
        else:
           self.accelerate()

    def avoid_collisions(self):
        # Teken een lijn naar de voorspelde positie en kijk of die een planeet snijdt
        predict_pos = self.next_pos(steps = self.__class__.time_in_advance / timestep) # from MovingObject
        linetest = LineHitbox(self.pos, predict_pos)
        swerving = False
        for planet in g.planets:
            if linetest.hit(planet):
                self.swerve(danger_object=planet)
                swerving = True
        return swerving      

    def check_visual(self):
        # Controleert of de speler zichtbaar is vanuit de gezichtskegel van de vijand
        delta = g.player.pos - self.pos
        if delta.magnitude_squared() > self.__class__.max_player_dist**2: 
            # Te ver weg: vergeet de speler onmiddellijk
            self.player_memory = 0
            return False
        if delta.normalize() * self.current_heading < math.cos(self.__class__.visual_cone_angle/2): 
            # Speler buiten de gezichtskegel
            return False
        # Controleer of er geen planeet de zichtlijn blokkeert
        linetest = LineHitbox(self.pos, g.player.pos)
        for planet in g.planets:
            if linetest.hit(planet):
                return False
        return True

    def resolve_ticker(self):
        # Voert langdurige acties uit (swerven, navigeren) zolang de ticker loopt
        if self.ticker == 0: return False
        if debug_enemy and self.ticker % 10 == 0:print(f'ticker {self.ticker}')
        self.ticker -= 1
        if self.longer_heading != None:
            # Vlieg in de opgeslagen richting
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
        # Richt op een positie, gecorrigeerd voor de eigen zijdelingse snelheid
        target_dir = (pos - self.pos)
        if target_dir.magnitude_squared() == 0:
            return False
        target_dir = target_dir.normalize()
        
        bullet_speed = self.__class__.bullet_type.speed
        # Bereken de zijdelingse snelheidscomponent ten opzichte van het doel
        perp_vel = self.vel - self.vel.dot(target_dir) * target_dir
        perp_speed = perp_vel.magnitude()
        
        if perp_speed >= bullet_speed:
            # Zijdelingse snelheid te groot: kogel kan het doel nooit bereiken
            self.turn_to(target_dir)
            return False
        
        # Bereken de vereiste voorhouding (lead angle) via de sinusregel
        lead_angle = math.degrees(math.asin(perp_speed / bullet_speed))
        # Roteer in de tegenovergestelde richting van de zijdelingse snelheid
        sign = -1 if target_dir.rotate(90).dot(perp_vel) > 0 else 1
        corrected_dir = target_dir.rotate(sign * lead_angle)
        
        self.turn_to(corrected_dir)
        # Geeft True terug als het schip nauwkeurig genoeg gericht is om te schieten
        return corrected_dir.dot(self.current_heading) > 0.95  

    def get_pos_pred(self, target):
        # Voorspelt de toekomstige positie van het doel op basis van de vluchttijd van de kogel
        bullet_speed = self.__class__.bullet_type.speed
    
        # Begin met de huidige positie als eerste schatting
        predict = target.pos
    
        for _ in range(self.__class__.pred_iterations):
            target_vect = predict - self.pos
            dist = target_vect.magnitude()
            if dist == 0:
                return target.pos
            target_dir = target_vect / dist
    
            # Bereken de effectieve snelheid van de kogel rekening houdend met de eigen snelheid
            straight_speed = self.vel * target_dir
            perp_speed_sq = (self.vel - straight_speed * target_dir).magnitude_squared()
            bullet_speed_sq = bullet_speed ** 2
            effective_speed = straight_speed + math.sqrt(bullet_speed_sq - perp_speed_sq) if bullet_speed_sq >= perp_speed_sq else straight_speed 
    
            if effective_speed <= 0:
                return target.pos
    
            travel_time = dist / effective_speed
            target_decimal_index = travel_time * fps / Spaceship.pos_estim_step_size
            delta = target_decimal_index - math.floor(target_decimal_index)
            floor_index = int(math.floor(target_decimal_index))
            ceil_index = floor_index + 1
            
            if target_decimal_index < 1.0:
                predict = (1 - target_decimal_index) * target.pos + target_decimal_index * target.position_estimation[0]
            elif ceil_index > 4:
                predict = target.position_estimation[4]
            else:
                predict = (1 - delta) * target.position_estimation[floor_index - 1] + delta * target.position_estimation[floor_index]
    
        self.aim_target = predict
        return predict

    def match_vel(self,target):
        # Pas de eigen snelheid aan zodat die overeenkomt met die van het doel
        if debug_enemy: self.status = 'matching vel'
        d_vel = target.vel - self.vel
        if d_vel * self.current_heading > 0:
            self.accelerate()
        if d_vel * self.current_heading < 0:
            self.decelerate()
        # Als het snelheidsverschil te groot is: draai eerst naar het doel
        if d_vel.magnitude_squared() >= self.__class__.max_rel_vel * 2: self.turn_to(target.pos-self.pos)   

    def pre_update(self):
        super().pre_update()
        if self.player_memory > 0:
            self.player_memory -= 1
        if self.check_visual():
            # Speler gezien: reset de geheugentimer
            self.player_memory = self.__class__.player_max_memory
        self.general_movement()
        if debug_enemy:
            if self.status != self.prev_satus:
                print(self.status)
                self.prev_satus = self.status

    def general_movement(self):
        # Prioriteitsvolgorde voor vijandgedrag (hoog naar laag)
        if self.avoid_collisions():
            return
        if self.resolve_ticker():
            return
        if self.player_memory > 0:
            self.player_interact() 
            return
        if self.force.magnitude_squared() > self.__class__.orbit_force_req**2 and self.strongest_grav != None:
            self.orbit(self.strongest_grav)  # Sterke zwaartekracht: ga in baan
            return
        if self.force.magnitude_squared() > self.__class__.planet_approach_req**2 and self.strongest_grav != None:
            if (self.vel - self.strongest_grav.vel) * (self.strongest_grav.pos - self.pos).normalize() < 250:
                # Nog niet snel genoeg richting planeet: navigeer ernaar toe
                self.navigate_to_point(self.strongest_grav.pos)
                return
        self.drift()  # Geen bijzondere situatie: vrij driften

    def player_interact(self):
        # Gedrag wanneer de vijand de speler heeft gezien of onthouden
        if self.bullet_ticker < self.__class__.pre_aim_ticks:
            # Bijna klaar om te schieten: begin te mikken op de voorspelde positie
            quality = self.aim(self.get_pos_pred(g.player))
            if self.bullet_ticker == 0 and quality: self.shoot()
            return
        if (self.pos - g.player.pos).magnitude_squared() > self.__class__.approach_dist ** 2: 
            # Speler te ver weg: beweeg naar hem toe
            self.navigate_to_point(g.player.pos)
        elif (self.vel - g.player.vel).magnitude_squared() > self.__class__.max_rel_vel ** 2:
            self.match_vel(g.player)
        else:
            # Dichtbij en stabiel: draai naar de speler klaar om te schieten
            self.turn_to(g.player.pos-self.pos)

    def kys(self):
        # Ken score toe als de speler deze vijand ooit geraakt heeft
        if self.hit_by_player: g.score_manager.add_score(self.__class__.score)
        super().kys()