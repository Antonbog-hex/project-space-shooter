import pygame
import traceback
import random
from sys import exit

# Klassen

class BasicObject(): 

# De meest fundamentele klasse. Elk object heeft een positie, alle andere klassen erven hiervan (direct of indirect)

    def __init__(self,pos: pygame.Vector2 = 0):
        self.pos = pygame.math.Vector2(pos)
    
    def update(self):
        pass # Lege methode, zodat super().update() altijd werkt

    def pre_update(self):
        pass # idem, deze methode wordt aangeroepen voor update()

class VisualObject(BasicObject):
# Object met zichtbare afbeelding, erft van BasicObject() -> heeft pos + image

    def __init__(self, image: pygame.Surface, **kwargs):
            if isinstance(image, str):
                image = pygame.image.load(image).convert_alpha()
            super().__init__(**kwargs)
            self.image = image
            self.base_image = self.image  # bewaar origineel voor rotaties

    def get_frame_pos(self) -> pygame.Vector2:
        offset = pygame.math.Vector2(self.image.get_width() // 2, self.image.get_height() // 2)
        return self.pos - offset

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

    def next_pos(self,steps = 1):
        # Berekent de positie na "steps" (kinematica)
        return self.pos + self.vel * timestep * steps + 0.5 * self.acc * (timestep * steps) ** 2

    def next_vel(self,steps = 1):
        # Berekent snelheid na "steps" (kinematica)
        return self.vel + self.acc * timestep*steps

    def update(self):
        self.pos = self.next_pos()
        self.vel = self.next_vel()
        super().update()

class GravityObject(BasicObject):
    # Object voor berekenen zwaartekrachten

    def __init__(self, mass: int = 200, **kwargs):
        super().__init__(**kwargs)
        self.mass = mass
        if isinstance(self, MovingObject):
            self.force = pygame.Vector2(0)

    def get_grav(self, other: "GravityObject"):
        # Berekent de zwaartekrachtsvector
        
        if self.pos == other.pos or not hasattr(self, 'force'):
            return
        diff = other.pos - self.pos
        dist_sq = diff.magnitude_squared()
        if dist_sq > 2000 ** 2:
            return  # Te ver weg: geen invloed

        # Standaard gravitatiewet: F = G * m1 * m2 / r²  (als vector)
        f = grav_cte * self.mass * other.mass * diff / dist_sq ** 1.5

        if isinstance(self, Spaceship):
            f += grav_cte * 0.01 * self.mass * other.mass * diff / dist_sq ** 1.3
        if f.magnitude_squared() < 50**2 and isinstance(self,Planet):
            return (0,0)
        return f
        
    def get_total_gravity(self):
        # Som van alle gravitatiekrachten van elk object
        force = pygame.Vector2(0)
        for object in active_object: #active_object is a global
            force += self.get_grav(object) or (0,0)
        return force

    def pre_update(self):
        # Wordt elke frame vóór update() aangeroepen om acc bij te werken.
        if isinstance(self, MovingObject):
            self.force = self.get_total_gravity()
            self.acc = self.force / self.mass
        super().pre_update() 

class RotatingObject(BasicObject):
    # Een object dat kan draaien.
    # angle        = huidige hoek in graden
    # angle_moment = draaisnelheid (zoals vel maar voor rotatie)
    def __init__(self,angle,angle_moment = 0,**kwargs):
         super().__init__(**kwargs)
         self.angle = angle
         self.angle_moment = angle_moment

    def angle_dampen(self):
        # Begrenst de draaisnelheid en vertraagt langzaam naar 0
        self.angle_moment = pygame.math.clamp(self.angle_moment, -150, 150)
        if self.angle_moment > 0: self.angle_moment -= 2
        if self.angle_moment < 0: self.angle_moment += 2

    def update(self):
        self.angle += self.angle_moment*timestep
        if isinstance(self, VisualObject): self.image = pygame.transform.rotozoom(self.base_image, self.angle, 1)
        super().update()

class Hitbox(BasicObject):
    # Basisklasse voor botsingsdetectie
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
    
    def hit(self,other: 'Hitbox') -> bool:
        pass

class CircularHitbox(Hitbox):
    # Ronde hitbox: botst als de afstand kleiner is dan de som van de radiussen
    def __init__(self,radius,**kwargs):
        super().__init__(**kwargs)
        self.hitbox_radius = radius

    def hit(self,other)-> bool:
        if isinstance(other, CircularHitbox):
            return (self.pos - other.pos).magnitude_squared() <= (self.hitbox_radius + other.hitbox_radius)**2 

class PhysicsObject(GravityObject,MovingObject,CircularHitbox):
    # Combineert zwaartekracht + beweging + botsingsdetectie. Dit is de basis voor planeten en spaceships.
    def __init__(self, pos,vel = 0, force = 0, mass = 20, hitbox_radius = 20, **kwargs):
        super().__init__(pos=pos,vel=vel, mass=mass, radius = hitbox_radius, **kwargs)

    def elastic_collision(self, other,energy_dis = 1):
         """
        Verwerkt een elastische botsing tussen dit object en "other".
        energy_dis < 1 = energie gaat verloren (inelastisch)
        energy_dis > 1 = energie wordt toegevoegd (explosief)
         """
         if other.pos == self.pos:
             return
         
         # Normal vector along collision axis
         relative = (other.pos - self.pos)
         normal = relative.normalize()
         overlap = relative.magnitude() - self.hitbox_radius - other.hitbox_radius
     
         # Relative velocity along normal
         rel_vel = self.vel - other.vel
         vel_along_normal = rel_vel.dot(normal)
         
         if vel_along_normal < 0:
             return # objects are moving apart
        
         # Elastic impulse scalar
         impulse = (2 * vel_along_normal) / (self.mass + other.mass)
         impulse = impulse * energy_dis

         # Apply impulse
         self.vel -= impulse * other.mass * normal
         self.pos += normal*0.51*overlap

         if isinstance(other,MovingObject):
             other.vel += impulse * self.mass * normal
             other.pos -= normal*0.51*overlap         

class ActiveObjects(list):
    # Lijst van alle actieve PhysicsObjects. Roept elke frame pre_update() en update() aan op elk object.

    def __init__(self):
        super().__init__()

    def add(self,other:PhysicsObject):
        self.append(other)

    def update(self):
        for e in self:
            e.pre_update() # calculates without action (eg. gravity)
        for e in self:
            e.update() # the action (eg. movement)

class Planet(PhysicsObject,VisualObject):
    # Een planeet: heeft een afbeelding, massa (gebaseerd op dichtheid+grootte) en botst elastisch met andere planeten.
    def __init__(self, pos, vel, style,density, size = 1):
        image = Planet.get_image(style,size)
        mass = 2500*density * size ** 2
        super().__init__(pos = pos ,image = image,vel=vel,mass = mass,hitbox_radius=size*255)
    
    def get_image(style,size):
        if style == 'icy':
            i = random.randint(0, 4)
            path = f'graphics/planets/Ice/{i}.png'
        elif style == 'tropical':
            i = random.randint(0,4)
            path = f'graphics/planets/Tropical/{i}.png'
        elif style == 'desert':
            i = random.randint(0,4)
            path = f'graphics/planets/Desert/{i}.png'
        elif style == 'ocean':
            i = random.randint(0,4)
            path = f'graphics/planets/Ocean/{i}.png'
        elif style == 'earth':
            i = random.randint(0,4)
            path = f'graphics/planets/Alpine/{i}.png'
        elif style == 'moon':
            i = random.randint(0,4)
            path = f'graphics/planets/Moons/{i}.png'
        else:
            raise ValueError(f'style:{style} is not supported')
        image = pygame.image.load(path).convert_alpha()
        image = pygame.transform.rotozoom(image, 0, size)
        return image

    def resolve_collisions(self):
        # Controleer botsingen met andere planeten (id-check voorkomt dubbele afhandeling)
        for sprite in active_object:
            if id(sprite)< id(self) and self.hit(sprite):
                if isinstance(sprite, Planet):
                    self.elastic_collision(sprite,energy_dis= 0.9)
                    
    def pre_update(self):
        if isinstance(self,MovingObject):
            self.resolve_collisions()
        super().pre_update()
    def update(self):
        super().update()
        

class Camera(BasicObject):
    # Beheert het scherm: achtergrond, objecten tekenen en vloeiend de speler volgen
    def __init__(self,screen):
        super().__init__()
        
        self.final_screen = screen
        
        #achtergrond
        self.background_surf = pygame.image.load('graphics/background/Starfield_05-1024x1024.png').convert()
        self.background_rect = self.background_surf.get_rect()
        self.background_pos = pygame.Vector2((0,0))
        
        self.zoom_level = 1.0
        self.min_zoom = 3
        self.max_zoom = 1
        self._rebuild_pre_screen()
    def _rebuild_pre_screen(self):
        # The pre_screen represents (true_width / zoom) world units
        # but is always rendered at the same pixel size
        effective_width = true_width / self.zoom_level
        effective_height = int(self.final_screen.get_height() / self.final_screen.get_width() * effective_width)
        self.pre_screen = pygame.Surface((int(effective_width), effective_height))
        self.scaler = self.final_screen.get_width() / effective_width
        self.screen_width = self.pre_screen.get_width()
        self.screen_height = self.pre_screen.get_height()
        self.offset = pygame.math.Vector2(self.screen_width / 2, self.screen_height / 2)
        
    def zoom(self, zoom_level):
        self.zoom_level = zoom_level
        self._rebuild_pre_screen()
    def track(self,target:'Player'):
        # Volg de speler vloeiend, kijk een beetje vooruit.
        
        
        desired_pos = target.position_estimation[1]  # fallback to current pos
        
       
        # Smooth lerp toward desired position
        LERP_SPEED = 0.08  # 0 = staat stil, 1 = springt direct
        
        delta = desired_pos - self.pos
        
        # Soft dead zone — scale down delta when close, don't hard-cut it
        dist = delta.magnitude()
        if dist > 0:
            # Ease out: slow down as we approach target
            
            self.pos += delta * LERP_SPEED 
        
        
        last_pred = target.position_estimation[-1]
        delta = (last_pred - self.pos).magnitude() + 100 
        base_half_h = (self.final_screen.get_height() / self.final_screen.get_width() * true_width) / 2
            
        required_zoom = base_half_h / delta if delta > 0 else self.base_zoom
        required_zoom = pygame.math.clamp(required_zoom, self.max_zoom, self.min_zoom)
        self.zoom_level += (required_zoom - self.zoom_level) * 0.05
        self._rebuild_pre_screen()
        
    def background_draw(self):
        # Tegelt de achtergrondafbeelding zodat hij oneindig groot lijkt.
        self.pre_screen.fill((0,0,0))
        bg_w = self.background_surf.get_width()
        bg_h = self.background_surf.get_height()
        
        
        top_left_x = self.pos.x - self.offset.x
        top_left_y = self.pos.y - self.offset.y
        
        # offset into the tile based on camera position
        start_x = -int(top_left_x % bg_w)
        start_y = -int(top_left_y % bg_h)
        
        
        # tile across the full screen
        x = start_x
        while x < self.screen_width:
            y = start_y
            while y < self.screen_height:
                self.pre_screen.blit(self.background_surf, (x, y))
                y += bg_w
            x += bg_h

    def debug_draw(self,group):
        # Tekent snelheidsvectoren en hitboxen (alleen zichtbaar als debug=True)
        if not hasattr(group,'__iter__'): # catches when attempting to draw a single object
            group = [group]
        for sprite in group:
            if isinstance(sprite, PhysicsObject):
                pos = sprite.pos
                pos = pos - self.pos + self.offset
                f = sprite.force
                a = f / sprite.mass
                pygame.draw.line(self.pre_screen, 'red', pos, pos+a)
                v = sprite.vel
                pygame.draw.line(self.pre_screen, 'orange', pos, pos+v)
            
            if isinstance(sprite, Player) and debug_player:
                pygame.draw.circle(self.pre_screen, 'blue', pos, sprite.hitbox_radius,width = 1)
            if isinstance(sprite, Planet) and debug_planet:
                pygame.draw.circle(self.pre_screen, 'green', pos, sprite.hitbox_radius,width = 1)

    def player_predict_draw(self):
        # Tekent de voorspelde baan van de speler als witte stippen
        for pos in player.position_estimation:
            pygame.draw.circle(self.pre_screen, 'white', pos - self.pos + self.offset , 4)
        
    def draw(self,group):
        # Tekent alle objecten in de groep op het scherm
        if not hasattr(group,'__iter__'): # catches when attempting to draw a single object
            group = [group]
        for sprite in group:
            pos = sprite.get_frame_pos() - self.pos + self.offset
            self.pre_screen.blit(sprite.image,pos)

    def finalise(self):
        # Schaal de pre_screen naar het echte venster en toon hem
        scaled = pygame.transform.rotozoom(self.pre_screen, 0, self.scaler)
        x = (self.final_screen.get_width() - scaled.get_width()) // 2
        y = (self.final_screen.get_height() - scaled.get_height()) // 2
        self.final_screen.blit(scaled, (x, y))
        
    
    def freecam(self):
        # Beweeg de camera vrij met de pijltjestoetsen
        keys = pygame.key.get_pressed()
        for key in keys:
            if keys[pygame.K_LEFT]:
                self.pos += (-0.05,0)
            if keys[pygame.K_RIGHT]:
                self.pos += (0.05,0)
            if keys[pygame.K_UP]:
                self.pos += (0,-0.05)
            if keys[pygame.K_DOWN]:
                self.pos += (0,0.05)    

class Spaceship(PhysicsObject,RotatingObject,VisualObject):
    # Een ruimteschip: combineert physics, rotatie en een afbeelding. Berekent ook een voorspelde baan.
    def __init__(self, pos, vel, angle,image ,**kwargs):
        super().__init__(pos = pos,image = image ,vel = vel , mass = 100, angle = angle , hitbox_radius= 15, **kwargs)
        self.position_estimation = []
    
    def pos_estimation_update(self,steps=5):
        # Simuleert de toekomstige baan door een kopie van het schip vooruit te bewegen zonder het echte schip aan te passen.
        active_object.remove(self)
        self.position_estimation.clear()
        
        tester = PhysicsObject(pos = self.pos,vel= self.vel,force = self.force,mass=self.mass,hitbox_radius= self.hitbox_radius)
        
        for i in range(steps):
            for i in range (32):
                tester.pre_update()
                tester.update()
            self.position_estimation.append(tester.pos)
        
        active_object.add(self)
                
    def collision_check(self):
        # Controleer of het schip een planeet raakt en stuit dan terug.
        for sprite in active_object:
            if self.hit(sprite):
                if isinstance(sprite, Planet):
                    self.elastic_collision(sprite,energy_dis= 1.1)
                                      
    def update(self):
        self.angle_dampen()
        self.collision_check()
        super().update()

class Player(Spaceship):
    # De door de speler bestuurde ruimteschip. Leest toetsinvoer en past versnelling/rotatie aan.
    def __init__(self, pos, vel, angle):
        super().__init__(pos = pos, image = 'graphics/player/spaceship1.png',vel = vel, angle = angle)
        self.base_image = pygame.transform.rotozoom(self.base_image, -90, 0.2)
    
    def input_check(self):
        # Verwerkt toetsinvoer: pijl omhoog = gas, links/rechts = draaien
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            a = pygame.math.Vector2()
            a.from_polar((400, -self.angle))
            if self.vel.dot(a) > 0:                            # check if  the force attempts increase in vel
                vel_norm = self.vel.normalize()
                a_parallel = vel_norm * a.dot(vel_norm)        # component along velocity
                a_perp = a - a_parallel                        # component perpendicular to velocity
                
                speed = self.vel.magnitude()
                dampen = 1 / (1 + speed * 0.01)
                self.acc += a_parallel * dampen + a_perp # only dampen parallel part
            else:
                self.acc += a
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.angle_moment += 20
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.angle_moment += -20
    
    def update(self):
        if not debug_freecam: self.input_check()
        self.pos_estimation_update()
        super().update()

# Hulpfuncties

def simpel_planet_spawn(player):
    #temperorary helper for planet tests
    pos = player.pos + pygame.Vector2(random.uniform(400, 800),random.uniform(400, 800))
    vel = pygame.Vector2(random.uniform(-200, 200),random.uniform(-200, 200))
    density = 2.5
    
    active_object.add(Planet(pos,vel,'icy',density,size=random.uniform(0.1,1.5)))

def random_planet_type():
    return random.choice(['icy','desert','earth','ocean','tropical'])

# Prefabs
all_prefabs = {}

def prefab_binary_planet(pos, density1=None, size1=None, density2 = None , size2 = None, separation=None):
    # Maakt twee planeten die om hun gemeenschappelijk zwaartepunt draaien. Als parameters weggelaten worden, worden willekeurige waarden gekozen.
    
    density1 = density1 or random.uniform(1,4)
    size1 = size1 or random.uniform(0.5,2)
    density2 = density2 or random.uniform(1,4)
    size2 = size2 or random.uniform(0.5,2)
    separation = separation or random.uniform(500,2000)
    
    mass1 = 2500 * density1 * size1**2
    mass2 = 2500 * density2 * size2**2
    
    # Afstand tot het gemeenschappelijk zwaartepunt
    total_mass = mass1 + mass2
    r1 = separation * mass2 / total_mass  # distance of body1 from CoM
    r2 = separation * mass1 / total_mass  # distance of body2 from CoM
    
    # Orbitale snelheid voor een cirkelvormige baan
    v1 = (grav_cte * mass2**2 / (total_mass * separation)) ** 0.5
    v2 = (grav_cte * mass1**2 / (total_mass * separation)) ** 0.5
    
    pos1 = pygame.Vector2(pos) + pygame.Vector2(-r1, 0)
    pos2 = pygame.Vector2(pos) + pygame.Vector2(r2, 0)
    
    p1 = Planet(pos1, (0, -v1), random_planet_type(), density1, size=size1)
    p2 = Planet(pos2, (0, v2), random_planet_type(), density2, size=size2)
    
    active_object.add(p1)
    active_object.add(p2)
    return p1, p2

def prefab_moon_system(pos, moon_count=3):
    # Maakt een centrale planeet met "moon_count" manen eromheen.
    central = Planet(pos, (0,0), random_planet_type(), 4.0, size=1.8)
    active_object.add(central)
    for i in range(moon_count):
        r = 800 + i * 300
        v = (grav_cte * central.mass / r) ** 0.5
        angle = random.uniform(0, 360)
        offset = pygame.Vector2(r, 0).rotate(angle)
        vel = pygame.Vector2(v, 0).rotate(angle + 90)
        active_object.add(Planet(pos + offset, vel, 'moon', 
                                 random.uniform(1,2), size=random.uniform(0.25, 0.55)))

# Main function

def main():
    if not debug_freecam:
        active_object.add(player)
    #prefab_binary_planet((0,4000))
    
    while True: 
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    prefab_moon_system(player.pos + (4000,0))
                
        # Beweeg alle objecten
        active_object.update()
        
        # Beweeg de camera
        if debug_freecam:
            camera.freecam()
        else:
            camera.track(player)
        
        # Teken alles
        camera.background_draw()
        camera.draw(active_object)
        camera.draw(player)
        camera.player_predict_draw()
        if debug:
            camera.debug_draw(player)
            camera.debug_draw(active_object)
        camera.finalise()
        #print(clock.get_fps())
        pygame.display.update()
        clock.tick(fps)
        print(camera.zoom_level)
        print(camera.pos)

#%% actually what runs 
# try-except prevents kernel crash in case of bug, because pygame needs to quit proper 
pygame.init()
try:
    random.seed(1234)
    info = pygame.display.Info()
    width = int(info.current_w * 0.9)   # 90% of screen width
    height = int(info.current_h * 0.9)  # 90% of screen height


    true_width = 4000 # change to alter game size
    screen = pygame.display.set_mode((width, height), pygame.SCALED) # Fix voor Mac computers met HIDPI-scaling
    screen_rect = screen.get_rect()
    debug = False
    debug_player = True
    debug_planet = True
    debug_freecam = False
    player = Player((0,0), (0,0), 0)
    camera = Camera(screen)
    clock = pygame.time.Clock()
    fps = 60
    timestep = 1/fps
    grav_cte = 6000
    active_object = ActiveObjects()
    
    main()
except:
    traceback.print_exc()
finally:
    pygame.quit()
