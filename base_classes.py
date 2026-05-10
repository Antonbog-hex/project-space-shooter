import pygame
import random
import gamestate as  g 
from constants import timestep,grav_cte, debug_world_gen # constant

class BasicObject(): 

# De meest fundamentele klasse. Elk object heeft een positie, alle andere klassen erven hiervan (direct of indirect)

    def __init__(self,pos: pygame.Vector2 = 0):
        self.pos = pygame.math.Vector2(pos)
        self._is_moving = False
        self._is_visual = False
        self._is_physics  = False 
    def update(self):
        pass # Lege methode, zodat super().update() altijd werkt

    def pre_update(self):
        pass # idem, deze methode wordt aangeroepen voor update()

    def kys(self):
        g.waste_bin.append(self)

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
        self._is_moving = True

    def next_pos(self,steps = 1):
        # Berekent de positie na "steps" (kinematica)
        return self.pos + self.vel * timestep * steps + 0.5 * self.acc * (timestep * steps) ** 2

    def next_vel(self,steps = 1):
        # Berekent snelheid na "steps" (kinematica)
        return self.vel + self.acc * timestep*steps
    
    def update(self):
        self.vel = self.next_vel()
        if self.vel.magnitude_squared() != 0:
            self.vel = self.vel.clamp_magnitude(1500) # Begrens de snelheid zodat objecten niet oneindig versnellen
        self.pos = self.next_pos()
        super().update()

class GravityObject(BasicObject):
    # Object voor berekenen zwaartekrachten
    grav_ticker = 3 # how many frames gravity gets recalculated
    def __init__(self, mass: int = 200, **kwargs):
        super().__init__(**kwargs)
        self.mass = mass
        # Spreidt de eerste gravitatieberekening willekeurig over meerdere frames,
        # zodat niet alle objecten tegelijk berekend worden (performance)
        self.grav_calc_ticker = random.randint(0,self.__class__.grav_ticker) # this ensures grav calc gets spread evenly
        self.reaction_f = pygame.Vector2(0) # this is a var used to lower grav calc using action-reaction principle
        self.force = pygame.Vector2(0)      # Totale kracht die op dit object werkt

    def get_grav(self, other: "GravityObject"):
        # Berekent de zwaartekrachtsvector van "other" op "self"
        if self._is_physics:
            # Kogels en predictors negeren de zwaartekracht van hun bronobject
            if self._is_bullet and self.source == other: return (0,0)
            if self._is_predictor and self.source == other: return (0,0)
        
        # Geen berekening nodig als de posities gelijk zijn of het object niet kan bewegen
        if self.pos == other.pos or not self._is_moving:
            return
        diff = other.pos - self.pos
        dist_sq = diff.magnitude_squared()
        if dist_sq > 2000 ** 2:
            return  # Te ver weg: geen invloed

        # Standaard gravitatiewet: F = G * m1 * m2 / r²  (als vector)
        f = grav_cte * self.mass * other.mass * diff / dist_sq ** 1.5

        # Spaceships krijgen een extra kleine aantrekkingskracht 
        # die minder snel afneemt zodat ze makkelijker in een baan blijven
        if self._is_spaceship:
            f += grav_cte * 0.01 * self.mass * other.mass * diff / dist_sq ** 1.3
        
        return f
        
    def get_total_gravity(self):
        # Som van alle gravitatiekrachten van elk object
        is_enemy = self._is_enemy
        if is_enemy:
            # Vijanden onthouden welke planeet het sterkst trekt (voor navigatie)
            strongest_grav = 0
            strongest_grav_source = None
        if self._is_planet:
            # Planeten starten met de reactiekracht die ze al ontvingen van andere planeten
            # (actie-reactieprincipe: vermijdt dubbele berekening)
            force = self.reaction_f
            self.reaction_f = pygame.Vector2(0)
        else:
            force = pygame.Vector2(0)
        
        for planet in g.planets: # enkel planeten zijn bronnen van gravitatie, spaceship-spaceship en dergelijke
                                 # aantrelling is computationeel zwaar en niet interessant voor gameplay 
            if planet is self:
                continue  # Een object trekt zichzelf niet aan
            if self._is_planet and id(self) > id(planet):
                continue  # handled already via reaction_f
            grav = self.get_grav(planet) or (0, 0)
            if self._is_planet:
                # Sla de reactiekracht op bij de andere planeet (Newton 3e wet)
                planet.reaction_f -= grav
            if is_enemy:
                grav_mag = grav[0] ** 2 + grav[1] ** 2
                if  grav_mag > strongest_grav:
                    strongest_grav = grav_mag
                    strongest_grav_source = planet                    
            force += grav
        if is_enemy: self.strongest_grav = strongest_grav_source
        return force

    def pre_update(self):
        # Wordt elke frame vóór update() aangeroepen om acc bij te werken.
        if  self._is_moving:
            # Bereken zwaartekracht niet elke frame, maar om de zoveel frames (grav_ticker)
            if  self.grav_calc_ticker == 0:
                self.force = self.get_total_gravity()
                self.acc = self.force / self.mass   # F = m*a  →  a = F/m
                self.grav_calc_ticker = self.__class__.grav_ticker
            else:
                self.grav_calc_ticker -= 1
        super().pre_update() 

class RotatingObject(BasicObject):
    # Een object dat kan draaien.
    # angle = huidige hoek in graden
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
        # Roteer het sprite-beeld mee als dit object visueel is
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
        pass  # Wordt overschreven door subklassen

class LineHitbox(Hitbox):
    def __init__(self,start_pos:pygame.Vector2,end_pos:pygame.Vector2):
        super().__init__(pos=start_pos)
        self.end = end_pos
        self.minx = min(self.pos.x,self.end.x)
        self.miny = min(self.pos.y,self.end.y)
        self.maxx = max(self.pos.x,self.end.x)
        self.maxy = max(self.pos.y,self.end.y)

    def hit(self,other):
        # Een lijn met lengte 0 kan niets raken
        if self.pos == self.end: return False
        if other._is_line:
            '''
            !!! this code is currently never used and may contain bugs !!!
            '''
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
            
            # Bereken de snijpuntparameters t en u
            # gebaseerd op Cramer's regel
            t = cross2d(other.pos - self.pos, d2) / denom
            u = cross2d(other.pos - self.pos, d1) / denom
            # intersection happens at self.pos + d1 * t or other.pos + d2 * u
            print(u,t)
            # Snijpunt bestaat alleen als beide parameters tussen 0 en 1 liggen
            return 0 <= t <= 1 and 0 <= u <= 1

        if other._is_circular:
            # Zoek het dichtstbijzijnde punt op het lijnstuk ten opzichte van de cirkel
            d = self.end - self.pos
            t = ((other.pos - self.pos) * d )/ (d*d)
            t = max(0.0, min(1.0, t))   # Klem t binnen het lijnstuk [0, 1]
            closest = self.pos + d * t
            # Raak als de afstand van dat punt tot het middelpunt kleiner is dan de straal
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
    # Combineert zwaartekracht + beweging + botsingsdetectie. Dit vormt de basis voor planeten en spaceships.
    def __init__(self, pos,vel = 0, force = 0, mass = 20, hitbox_radius = 20, **kwargs):
        super().__init__(pos=pos,vel=vel, mass=mass, radius = hitbox_radius, **kwargs)
        self._is_physics = True
        self._is_planet = False
        self._is_spaceship = False
        self._is_enemy = False
        self._is_bullet = False
        self._is_predictor = False
        self._is_target = False
        self._is_player = False
        self._is_item = False

    def elastic_collision(self, other,energy_dis = 1, reflective = True , damage_multiplier = 0):
         """
        Verwerkt een elastische botsing tussen dit object en "other".
        energy_dis < 1 = energie gaat verloren 
        energy_dis > 1 = energie wordt toegevoegd
         """
         if other.pos == self.pos:
             return  # Voorkom deling door nul bij volledig overlappende posities
         
         # Normal vector along collision axis
         relative = (other.pos - self.pos)
         normal = relative.normalize()
         overlap = relative.magnitude() - self.hitbox_radius - other.hitbox_radius
     
         # Relative velocity along normal
         rel_vel = self.vel - other.vel
         vel_along_normal = rel_vel * normal
         
         if vel_along_normal < 0:
             return # objects are moving apart
        
         # Berekent de impuls op basis van de massa's en de relatieve snelheid
         # dit is een resultaat gebaseerd op behoud van energie en impuls
         impulse = (2 * vel_along_normal) / (self.mass + other.mass)
         
         if damage_multiplier != 0:
             # Schade is afhankelijk van de botsingssnelheid; langzame botsingen doen geen schade
             damage = int(vel_along_normal/100 - 4)  * damage_multiplier  # pas 100 aan voor meer of minder schade; 100 px/s = 1 HP
             if damage > 0:
                 if self._is_spaceship: self.take_damage(damage)
                 if other._is_spaceship: other.take_damage(damage)
         
         impulse = impulse * energy_dis
         # Pas de impuls toe op de snelheden en corrigeer de overlappende posities
         self.vel -= impulse * other.mass * normal
         self.pos += normal*0.51*overlap  # Schuif iets meer dan de helft om blijvende overlap te vermijden

         if other._is_moving and reflective:
             # Spiegel de impuls op het andere object als het ook beweegt
             other.vel += impulse * self.mass * normal
             other.pos -= normal*0.51*overlap
        
    def pre_update(self):
        # Controleer of het object nog binnen de veilige zone van de chunkmanager valt
        if not g.chunkmanager.in_safezone(self.pos):
            try:
                # Verplaats het object naar de juiste chunk als het buiten de safezone is
                g.chunkmanager.all_chunks[g.chunkmanager.get_chunk(self.pos)].append(self)
                if debug_world_gen and not self._is_predictor:
                    print(f'unloaded{self}')
            except:
                # Het object bevond zich in een nooit geladen chunk en wordt vernietigd
                if debug_world_gen: print(f"{self} entered a never before loaded chunk and was destroyed")
            finally:
                self.kys()
        super().pre_update()