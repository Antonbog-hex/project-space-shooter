import pygame
import traceback
import random
import math


# Klassen
# %% basic classes
class BasicObject(): 

# De meest fundamentele klasse. Elk object heeft een positie, alle andere klassen erven hiervan (direct of indirect)

    def __init__(self,pos: pygame.Vector2 = 0):
        self.pos = pygame.math.Vector2(pos)
    
    def update(self):
        pass # Lege methode, zodat super().update() altijd werkt

    def pre_update(self):
        pass # idem, deze methode wordt aangeroepen voor update()
    def kys(self):
        
        try:
            active_object.remove(self)
        except:
            pass
        try:
            bullets.remove(self)
        except:
            pass
            
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
        
        self.vel = self.next_vel()
        if self.vel.magnitude_squared() != 0:
            self.vel = self.vel.clamp_magnitude(1500)
        self.pos = self.next_pos()
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
        if isinstance(self,Bullet) and self.source == other: return (0,0)
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
        if f.magnitude_squared()/self.mass < 200**2 and isinstance(self,Planet):
            return (0,0)
        
        return f
        
    def get_total_gravity(self):
        # Som van alle gravitatiekrachten van elk object
        is_enemy = isinstance(self, BaseEnemy)
        if is_enemy:
            strongest_grav = 0
            strongest_grav_source = None
        force = pygame.Vector2(0)
        for object in active_object: #active_object is a global
            grav =  self.get_grav(object) or (0,0)
            if is_enemy:
                grav_mag = grav[0] ** 2 + grav[1] ** 2
                if  grav_mag > strongest_grav:
                    strongest_grav = grav_mag
                    strongest_grav_source = object
            force += grav
        if is_enemy:self.strongest_grav = strongest_grav_source
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
        self.angle_moment = pygame.math.clamp(self.angle_moment, -250, 250)
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
class LineHitbox(BasicObject):
    def __init__(self,start_pos:pygame.Vector2,end_pos:pygame.Vector2):
        super().__init__(pos=start_pos)
        self.end = end_pos
        self.minx = min(self.pos.x,self.end.x)
        self.miny = min(self.pos.y,self.end.y)
        self.maxx = max(self.pos.x,self.end.x)
        self.maxy = max(self.pos.y,self.end.y)
    def hit(self,other):
        if isinstance(other, LineHitbox):
            #currenlty unused, may be faulthy
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
            
            t = cross2d(other.pos - self.pos, d2) / denom
            u = cross2d(other.pos - self.pos, d1) / denom
            # intersection happens at self.pos + d1 * t or other.pos + d2 * u
            print(u,t)
            return 0 <= t <= 1 and 0 <= u <= 1
        if isinstance(other, CircularHitbox):
            d = self.end - self.pos
            t = (other.pos - self.pos).dot(d) / d.dot(d)
            t = max(0.0, min(1.0, t))
            closest = self.pos + d * t
            return (closest - other.pos).magnitude_squared() <= other.hitbox_radius ** 2
class CircularHitbox(Hitbox):
    # Ronde hitbox: botst als de afstand kleiner is dan de som van de radiussen
    def __init__(self,radius,**kwargs):
        super().__init__(**kwargs)
        self.hitbox_radius = radius

    def hit(self,other)-> bool:
        if isinstance(other, CircularHitbox):
            return (self.pos - other.pos).magnitude_squared() <= (self.hitbox_radius + other.hitbox_radius)**2 
        if isinstance(other, LineHitbox):
            return other.hit(self)
# %% combined classes
class PhysicsObject(GravityObject,MovingObject,CircularHitbox):
    # Combineert zwaartekracht + beweging + botsingsdetectie. Dit is de basis voor planeten en spaceships.
    def __init__(self, pos,vel = 0, force = 0, mass = 20, hitbox_radius = 20, **kwargs):
        super().__init__(pos=pos,vel=vel, mass=mass, radius = hitbox_radius, **kwargs)

    def elastic_collision(self, other,energy_dis = 1, reflective = True):
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

         if isinstance(other,MovingObject) and reflective:
             other.vel += impulse * self.mass * normal
             other.pos -= normal*0.51*overlap       
    def pre_update(self):
        if isinstance(self,Predictor):
            pass
        elif not chunkmanager.in_safezone(self.pos):
            
            try:
                chunkmanager.all_chunks[chunkmanager.get_chunk(self.pos)].append(self)
                if not isinstance(self, Predictor):
                    if debug_world_gen: print(f'unloaded{self}')
            except:
                if debug_world_gen: print(f"{self} entered a never before loaded chunk and was destroyed")
            finally:
                self.kys()
        super().pre_update()
                
class Predictor(PhysicsObject):
    def pre_update(self):
        GravityObject.pre_update(self)
    def update(self):
        for obj in active_object:
            if self.hit(obj) and obj != player:
                self.elastic_collision(obj,energy_dis=1.1,reflective=False)
        super().update()

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
class Camera(BasicObject):
    # Beheert het scherm: achtergrond, objecten tekenen en vloeiend de speler volgen
    max_width = 5000 # the max width to zoom out to
    min_width = 1000 # the min width to zoom into
    def __init__(self,screen):
        super().__init__()
        
        self.final_screen = screen # what actually gets shown
        
        #achtergrond
        self.background_surf = pygame.image.load('graphics/background/Starfield_05-1024x1024.png').convert()
        self.background_rect = self.background_surf.get_rect()
        self.background_pos = pygame.Vector2((0,0))
        
        self.zoom_level = 1.0
        self.min_zoom = __class__.min_width / true_width
        self.max_zoom = __class__.max_width / true_width
        self._rebuild_pre_screen()
    def _rebuild_pre_screen(self):
        # The pre_screen represents (true_width / zoom) world units
        # but is always rendered at the same pixel size
        effective_width = true_width * self.zoom_level
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
   
        desired_pos = target.position_estimation[1] if (target.position_estimation[1]-target.pos).magnitude_squared() < 500 ** 2 else target.pos # fallback to current pos
        # Smooth lerp toward desired position
        LERP_SPEED = 0.08  # 0 = staat stil, 1 = springt direct
        delta = desired_pos - self.pos
        self.pos += delta * LERP_SPEED 
        
        
        last_pred = target.position_estimation[-1]
        desired_height = (last_pred - target.pos).magnitude() + 50 
        desired_height *= 2
        base_half_h = self.final_screen.get_height() 
            
        required_zoom =  desired_height/base_half_h if desired_height > 0 else self.base_zoom
        required_zoom = pygame.math.clamp(required_zoom, self.min_zoom, self.max_zoom)
        self.zoom_level += (required_zoom - self.zoom_level) * 0.05 # LERP zoom
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
                a = sprite.acc
                if a.magnitude_squared() != 0: a=a.clamp_magnitude(800)
                pygame.draw.line(self.pre_screen, 'red', pos, pos+a)
                v = sprite.vel
                if v.magnitude_squared() != 0: v=v.clamp_magnitude(800)
                pygame.draw.line(self.pre_screen, 'orange', pos, pos+v)
            if isinstance(sprite, Target):
                pygame.draw.circle(self.pre_screen, 'green', pos, sprite.hitbox_radius,width = 1)
            if isinstance(sprite, BaseEnemy):
                pygame.draw.line(self.pre_screen,'white',pos,pos + sprite.current_heading * 100)
                pygame.draw.circle(self.pre_screen, 'green', pos, sprite.hitbox_radius,width = 1)
                if sprite.desired_heading != None:
                    pygame.draw.line(camera.pre_screen, 'purple', pos, pos + sprite.desired_heading.normalize() * 100)
                if sprite.aim_target != None:
                    target = sprite.aim_target - self.pos + self.offset
                    pygame.draw.circle(self.pre_screen, 'magenta', target , 5)
            if isinstance(sprite, Player) and debug_player:
                pygame.draw.circle(self.pre_screen, 'blue', pos, sprite.hitbox_radius,width = 1)
            if isinstance(sprite, Planet) and debug_planet:
                pygame.draw.circle(self.pre_screen, 'green', pos, sprite.hitbox_radius,width = 1)

    def player_predict_draw(self):
        # Tekent de voorspelde baan van de speler als witte stippen
        for pos in player.position_estimation:
            pygame.draw.circle(self.pre_screen, 'white', pos - self.pos + self.offset , 4)
        
    def draw(self, group):
        if not hasattr(group, '__iter__'):
            group = [group]
        for sprite in group:
            pos = sprite.get_frame_pos() - self.pos + self.offset
            self.pre_screen.blit(sprite.image, pos)
    
            if isinstance(sprite, BaseEnemy):
                bar_width  = 40
                bar_height = 5
                center_pos = sprite.pos - self.pos + self.offset
    
                bg_rect = pygame.Rect(center_pos.x - bar_width // 2, center_pos.y - 22, bar_width, bar_height)
                pygame.draw.rect(self.pre_screen, (150, 0, 0), bg_rect)
    
                hp_fraction = sprite.hp / sprite.max_hp
                hp_rect = pygame.Rect(center_pos.x - bar_width // 2, center_pos.y - 22, int(bar_width * hp_fraction), bar_height)
                pygame.draw.rect(self.pre_screen, (0, 200, 0), hp_rect)
        

    def finalise(self):
        # Schaal de pre_screen naar het echte venster en toon hem
        scaled = pygame.transform.rotozoom(self.pre_screen, 0, self.scaler)
        x = (self.final_screen.get_width() - scaled.get_width()) // 2
        y = (self.final_screen.get_height() - scaled.get_height()) // 2
        self.final_screen.blit(scaled, (x, y))
        
    
    def freecam(self):
        # Beweeg de camera vrij met de pijltjestoetsen
        keys = pygame.key.get_pressed()
        scroll_speed = 20
        if keys[pygame.K_LEFT] or keys[pygame.K_a] :
            self.pos += (-scroll_speed,0)
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.pos += (scroll_speed,0)
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.pos += (0,-scroll_speed)
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.pos += (0,scroll_speed) 
        if keys[pygame.K_q]:
            self.zoom(self.zoom_level + 0.01)
        if keys[pygame.K_e]:
            self.zoom(self.zoom_level - 0.01)
class Bullet(PhysicsObject, VisualObject):
# Een kogel die het schip afvuurt.
    damage = 1
    speed = 800
    lifetime = 180
    def __init__(self, pos, vel, source):
        # Maak een klein oranje cirkeltje als afbeelding voor de kogel
        bullet_surface = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.circle(bullet_surface, (255, 180, 50), (4, 4), 4)
        super().__init__(pos=pos, vel=vel, mass=1, hitbox_radius=4,image=bullet_surface)
        self.source = source
        self.lifetime = self.__class__.lifetime   # frames it lives

    def check_collisions(self):
        for obj in active_object:
            if obj != self.source and self.hit(obj):
                if isinstance(obj, Planet):
                    self.kys()
                elif isinstance(obj, Target):
                    obj.kys()
                    self.kys()
                elif isinstance(obj, BaseEnemy):
                    obj.take_damage(self.__class__.damage)
                    self.kys()
    def update(self):
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kys()
        self.check_collisions()
        super().update()
                
class Spaceship(PhysicsObject,RotatingObject,VisualObject):
    pos_estim_step_size = 20# number of frames that get predicted per step
    max_hp = 1
    bullet_type = Bullet
    speed =  500
    bullet_reload = 30
    
    # Een ruimteschip: combineert physics, rotatie en een afbeelding. Berekent ook een voorspelde baan.
    def __init__(self, pos, vel, angle,image,hitbox_radius = None ,**kwargs):
        hitbox_radius = hitbox_radius or 15
        super().__init__(pos = pos,image = image ,vel = vel , mass = 100, angle = angle , hitbox_radius= hitbox_radius, **kwargs)
        self.position_estimation = [self.pos for i in range(5)]
        self.hp = self.__class__.max_hp
        self.bullet_ticker = self.__class__.bullet_reload
        self.current_heading = pygame.Vector2.from_polar((1, -self.angle)) # direction of pointing normvector
    def accelerate(self):
        self.acc += self.current_heading * self.speed
    def decelerate(self):
        self.acc -= self.current_heading * self.speed * 0.5
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
        self.hp -= amount
        if self.hp <= 0:
            self.kys()  
    def shoot(self):
        if self.bullet_ticker > 0 : return
        bullet = __class__.bullet_type(self.pos,self.vel + self.current_heading * self.__class__.bullet_type.speed,self)
        bullets.add(bullet)      
        self.bullet_ticker = self.__class__.bullet_reload         
    def collision_check(self):
        # Controleer of het schip een planeet raakt en stuit dan terug.
        for sprite in active_object:
            if id(sprite) < id (self) and self.hit(sprite):
                if isinstance(sprite, Planet):
                    self.elastic_collision(sprite,energy_dis= 1.1)
                if isinstance(sprite,Spaceship):
                    self.elastic_collision(sprite, energy_dis = 1.4)
    def _orientation_update(self):
        self.current_heading = pygame.Vector2.from_polar((1, -self.angle))
    def update(self):
        if self.bullet_ticker > 0 : self.bullet_ticker -= 1
        self.angle_dampen()
        self.collision_check()
        super().update()
    def pre_update(self):
        self._orientation_update()
        super().pre_update()
class ChunkManager:
    def __init__(self,chunk_size = (2000,2000),around_chunks = 1):
        self.chunk_size = chunk_size
        self.chunk_x = self.chunk_size[0]
        self.chunk_y = self.chunk_size[1]
        self.around_chunks = around_chunks
        self.central_chunk = (0,0)
        self.all_chunks = {}
        self.active_chunks = set()
        self.min_x = 0
        self.max_x = 0
        self.min_y = 0
        self.max_y = 0
    
    def get_chunk(self,pos:pygame.Vector2):
        return (int(pos.x // self.chunk_x ), int(pos.y //self.chunk_y))
    def set_active(self,chunk):
        self.active_chunks.add(chunk)
        try:
            for element in self.all_chunks[chunk]:
                active_object.add(element)
        except:
            if not debug_disable_world_gen:
                self.generate_chunk(chunk)
            self.all_chunks[chunk] = []
        
    def set_inactive(self,chunk):
        self.active_chunks.remove(chunk)
    def active_chunk_update(self):
        new_active_chunk = set()
        for i in range(self.central_chunk[0]-self.around_chunks,self.central_chunk[0]+self.around_chunks+1):
            for j in range(self.central_chunk[1]-self.around_chunks,self.central_chunk[1]+self.around_chunks+1):
                chunk = (i,j)
                new_active_chunk.add(chunk)
        for chunk in new_active_chunk.difference(self.active_chunks):
            self.set_active(chunk)
        for chunk in self.active_chunks.difference(new_active_chunk):
            self.set_inactive(chunk)
        self.active_chunks = new_active_chunk
    def calculate_safezone(self):
        self.min_x = (self.central_chunk[0] - self.around_chunks) * self.chunk_size[0]
        self.max_x = (self.central_chunk[0] + self.around_chunks+1) * self.chunk_size[0]
        self.min_y = (self.central_chunk[1] - self.around_chunks) * self.chunk_size[1]
        self.max_y = (self.central_chunk[1] + self.around_chunks+1) * self.chunk_size[1]
    def in_safezone(self,pos:pygame.Vector2):
        if pos.x < self.max_x and pos.x > self.min_x and pos.y < self.max_y and pos.y > self.min_y:
            return True
        return False
    def get_center(self,chunk): 
        return pygame.Vector2((chunk[0] + 0.5 )*self.chunk_x,(chunk[1] + 0.5 )*self.chunk_y)
    def generate_chunk(self, chunk):
        chunk_center = self.get_center(chunk)
        random_pos = 500
        chunk_center += pygame.Vector2(random.uniform(-random_pos, random_pos),random.uniform(-random_pos, random_pos))
        prefab = random.choice(list(all_prefabs.values()))
        self.all_chunks[chunk] = prefab(chunk_center)
            
    def update(self):
        self.central_chunk = self.get_chunk(player.pos)
        self.active_chunk_update()
        self.calculate_safezone()
        
        
        
        
# %% finished classes
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
        elif style == 'black_hole':
            path = 'graphics/planets/BlackHole/0.png'
        elif style == 'sattelite':
            path = 'graphics/planets/Satellite/0.png'
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
                if isinstance(sprite, Spaceship):
                    self.elastic_collision(sprite,energy_dis= 1.5)
              
    def pre_update(self):
        if isinstance(self,MovingObject):
            self.resolve_collisions()
        super().pre_update()
    def update(self):
        
        super().update()   
class Player(Spaceship):
    bullet_reload = 15
    max_hp = 15
    # De door de speler bestuurde ruimteschip. Leest toetsinvoer en past versnelling/rotatie aan.
    def __init__(self, pos, vel, angle):
        self.shoot_cooldown = 0
        super().__init__(pos = pos, image = 'graphics/player/player.png',vel = vel, angle = angle)
        self.base_image = pygame.transform.rotozoom(self.base_image, -90, 0.04)
        self.image = self.base_image
    def input_check(self):
        # Verwerkt toetsinvoer: pijl omhoog = gas, links/rechts = draaien
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            
            if self.vel * self.current_heading < 300:
                self.accelerate()
            else:
                perp = self.vel.rotate(90).normalize()
                self.acc += self.speed * (self.current_heading  * perp) * perp
                
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.angle_moment += 20
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.angle_moment += -20
        if keys[pygame.K_SPACE]:
            self.shoot()
    def angle_dampen(self):
        self.angle_moment = pygame.math.clamp(self.angle_moment, -150, 150)
        super().angle_dampen()
    def update(self):
        if not debug_freecam: self.input_check()
        self.pos_estimation_update()
        super().update()
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
    
class BaseEnemy(Spaceship):
    # Dit is een basis vijand, alle andere vijanden erven hiervan
    # Verander deze waarden in de subklassen om een ander type vijand te maken
    spawn_weight = 1      # hoe groter, hoe vaker dit type spawnt - to be implemented
    bullet_type = Bullet
    bullet_reload = 180 # ticks to reload
    image_path = 'graphics/enemies/enemy_1.png' 
    hitbox_radius = 25
    max_hp = 3
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
        if debug_enemy:
            self.status= '' # string that states what enemies does this tick
            self.prev_satus = '' # string that states what enemies does prev tick 
            self.aim_target = None
    def turn_to(self,heading):
        turn_error = signed_angle_to( self.current_heading, heading)
        self.angle_moment += turn_error * 2 - self.angle_moment * 0.1  # tune this multiplier         
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
        if perp_speed > 50:
            correction = (-vel_perp.normalize()) * min(perp_speed / 300, 1.0)
            desired_heading = (desired_heading + correction).normalize()
        self.desired_heading = desired_heading
        self.turn_to(desired_heading)
    
        # velocity component toward the target
        vel_toward = self.vel.dot(desired_heading)
        
        # braking distance: how far we travel before stopping at current speed
        # to prevent overshoot
        braking_acc = self.speed * 0.5  # matches decelerate()
        braking_dist = (vel_toward ** 2) / (2 * braking_acc) if vel_toward > 0 else 0
    
        aligned = self.current_heading *desired_heading > 0.7
    
        if braking_dist >= dist * 0.8:
            # close to overshoot — brake
            self.decelerate()
        elif vel_toward < 300 and aligned:
            self.accelerate()
    def drift(self):
        # basic movement if nothing is around
        if debug_enemy: self.status = 'drifting'
        self.turn_to(self.vel)
        if self.vel.magnitude_squared() > 400 **2:
            self.decelerate()
        elif self.vel.magnitude_squared() < 350 ** 2:
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
        desired_cw = delta.rotate(100)
        desired_ccw = delta.rotate(-100)
        
        if self.current_heading * desired_cw >  self.current_heading * desired_ccw: #uses inproduct as a metric of alignedness
            desired_heading = desired_cw
            
        else:
            desired_heading = desired_ccw
            
        self.desired_heading = desired_heading
        self.longer_heading = desired_heading
        self.ticker = 45
        self.turn_to(desired_heading)
        if self.current_heading * delta > 0:
            self.decelerate()
        else:
           self.accelerate()
    def avoid_collisions(self):
        predict_pos = self.next_pos(steps = 2 * fps)
        linetest = LineHitbox(self.pos, predict_pos)
        swerving = False
        for obj in active_object:
            if isinstance(obj, Planet) and linetest.hit(obj):
                self.swerve(danger_object=obj)
                swerving = True
        return swerving      
    def check_visual(self):
        delta = player.pos - self.pos
        if delta.magnitude_squared() > 2500**2: 
            self.player_memory = 0
            return False
        if delta.normalize() * self.current_heading < math.cos(50): 
            return False
        linetest = LineHitbox(self.pos, player.pos)
        for obj in active_object:
            if isinstance(obj,Planet) and linetest.hit(obj):
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
    def general_movement(self):
        if self.avoid_collisions():
           return
        if self.resolve_ticker():
            return
        if self.player_memory > 0:
            self.player_interact()
            return
        if self.force.magnitude_squared() > 5000**2 and self.strongest_grav != None:
            self.orbit(self.strongest_grav)
            return
        if self.force.magnitude_squared() > 2000**2 and self.strongest_grav != None:
            if (self.vel - self.strongest_grav.vel) * (self.strongest_grav.pos - self.pos).normalize() < 250: # check if youre already approaching
                self.navigate_to_point(self.strongest_grav.pos)
                return
        self.drift()
    def player_interact(self):
        
        if (self.pos - player.pos).magnitude_squared() > 500 ** 2: 
            self.navigate_to_point(player.pos)
        elif (self.vel - player.vel).magnitude_squared() > 150 ** 2:
            self.match_vel(player)
        else:self.aim(self.get_pos_pred(player))
        if self.bullet_ticker < 30:
            self.aim(self.get_pos_pred(player))
            if self.bullet_ticker == 0: self.shoot()
               
        
    def aim(self, pos):
        self.turn_to(pos-self.pos)
        '''
        target_vect = pos - self.pos
        target_dir = target_vect.normalize()
        
        bullet_speed = self.__class__.bullet_type.speed
        
        # decompose own velocity into components
        perp_vel = self.vel - self.vel.dot(target_dir) * target_dir  # velocity perpendicular to target
        perp_speed = perp_vel.magnitude()
        
        # lead angle from trig: sin(a) = perp_speed / bullet_speed
        if perp_speed < bullet_speed:  # avoid domain error
            lead_angle = math.degrees(math.asin(perp_speed / bullet_speed))
            # rotate toward the side the perp vel is pushing
            sign = -1 if target_dir.rotate(90).dot(perp_vel) > 0 else 1
            corrected_dir = target_dir.rotate(sign * lead_angle)
        else:
            corrected_dir = target_dir  # fallback, cant compensate
        
        self.turn_to(corrected_dir)
        return corrected_dir.dot(self.current_heading) > 0.8
        '''
        
        
    def get_pos_pred(self, target):
        target_vect = target.pos - self.pos
        dist = target_vect.magnitude()
        target_dir = target_vect / dist
        
        bullet_speed = self.__class__.bullet_type.speed
        # relative closing speed along the target direction
        relative_vel = (self.vel - target.vel).dot(target_dir)
        effective_speed = bullet_speed + relative_vel
        
        if effective_speed <= 0:  # bullet can never reach target
            return target.pos
        
        travel_time = dist / effective_speed
        target_decimal_index = max(0, (travel_time * fps / Spaceship.pos_estim_step_size) - 1)
        delta = target_decimal_index - math.floor(target_decimal_index)
        floor_index = int(math.floor(target_decimal_index))
        
        if floor_index == 0 and target_decimal_index < 1:
            # interpolate between current pos and first prediction
            predict = (1 - delta) * target.pos + delta * target.position_estimation[0]
        elif floor_index >= 4:
            predict = target.position_estimation[4]
        else:
            predict = ((1 - delta) * target.position_estimation[floor_index - 1]
                           + delta * target.position_estimation[floor_index])
        self.aim_target = predict
        return predict
    def match_vel(self,target):
        if debug_enemy: self.status = 'matching vel'
        d_vel = target.vel - self.vel
        if d_vel * self.current_heading > 0:
            self.accelerate()
        if d_vel * self.current_heading < 0:
            self.decelerate()
        self.turn_to(target.pos-self.pos)   
    def pre_update(self):
        super().pre_update()
        
        keys = pygame.key.get_pressed()
        if keys[pygame.K_l]:
            self.aim(self.get_pos_pred(player)) #debug
            
        if self.player_memory > 0:
            self.player_memory -= 1
        if self.check_visual():
            self.player_memory = 300
        
        self.general_movement()
        if debug_enemy:
            if self.status != self.prev_satus:
                print(self.status)
                self.prev_satus = self.status
class Enemy1(BaseEnemy):
    # Snel maar lage hp
    hp           = 3
    max_hp       = 3
    speed        = 600
    damage       = 20
    spawn_weight = 2   # spawnt vaker dan EnemyBrute

class Enemy2(BaseEnemy):
    # Traag maar hoge hp
    hp           = 8
    max_hp       = 8
    speed        = 180
    damage       = 40
    spawn_weight = 1   # spawnt het minst vaak

# Lijst van alle vijandtypes — voeg hier nieuwe types toe als je ze maakt
all_enemy_types = [BaseEnemy, Enemy1, Enemy2]    

class DebugMass(PhysicsObject,VisualObject):
    def __init__(self):
        image = pygame.Surface((20,20))
        pygame.draw.circle(image,'red',(10,10),10)
        super().__init__((50,50),mass = 300,image=image .convert_alpha())
    def update(self):
        if pygame.mouse.get_pressed()[0]:
            self.mass = 1000
            mouse_screen = pygame.Vector2(pygame.mouse.get_pos())
            # convert screen pixels to pre_screen coordinates
            mouse_pre = mouse_screen / camera.scaler
            # convert pre_screen coordinates to world coordinates
            mouse_world = mouse_pre - camera.offset + camera.pos
            self.pos = mouse_world
            self.vel = pygame.Vector2(0)
        else:
            self.mass = 0.01
            self.vel = pygame.Vector2(0)
        super().update()
                   
    


class Target(PhysicsObject, VisualObject):
# Een doelobject om op te schieten.

    def __init__(self, pos, vel=(0, 0), size=1.0):
        # Grootte in pixels, schaalbaar via size
        pixel_size = int(60 * size)   
        hitbox = int(30 * size)

        target_surface = pygame.Surface((pixel_size, pixel_size), pygame.SRCALPHA)
        pygame.draw.rect(target_surface, (220, 50, 50), (0, 0, pixel_size, pixel_size), border_radius=6)
        pygame.draw.rect(target_surface, (255, 100, 100), (0, 0, pixel_size, pixel_size), width=2, border_radius=6)

        super().__init__(pos=pos, vel=vel, mass=10, hitbox_radius=hitbox, image=target_surface)
    
    def update(self):
        super().update()


#%% Hulpfuncties

def simpel_planet_spawn(pos,vel= None):
    #temperorary helper for planet tests
    vel = vel or pygame.Vector2(random.uniform(-200, 200),random.uniform(-200, 200))
    density = 2.5
    
    active_object.add(Planet(pos,vel,random_planet_type(),density,size=random.uniform(1,1.5)))

def random_planet_type():
    return random.choice(['icy','desert','earth','ocean','tropical'])

def signed_angle_to(v1, v2):
    # cross product gives sin of angle, dot gives cos
    cross = -(v1.x * v2.y - v1.y * v2.x) # negation to fix weirdness with pygames inverted y
    dot = v1.dot(v2)
    return math.degrees(math.atan2(cross, dot))
#%% Prefabs


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

def spawn_in_orbit(center_pos, anchor_mass, r, angle, style, density, size):
    v = (grav_cte * anchor_mass / r) ** 0.5
    offset = pygame.Vector2(r, 0).rotate(angle)
    vel = pygame.Vector2(v, 0).rotate(angle + 90)
    planet = Planet(center_pos + offset, vel, style, density, size=size)
    active_object.add(planet)
    return planet

def prefab_moon_system(pos, moon_count=None):
    central = Planet(pos, (0,0), random_planet_type(), 4.0, size=1.8)
    active_object.add(central)

    moon_count = moon_count or random.randint(1, 4)
    spawned = [central]
    for i in range(moon_count):
        r = 800 + i * 300
        angle = (360 / moon_count) * i
        moon = spawn_in_orbit(pos, central.mass, r, angle,'moon', random.uniform(1, 2), random.uniform(0.25, 0.55))
        spawned.append(moon)
    return spawned


def prefab_asteroid_field(pos, count=None):
    count = count or random.randint(6, 12)
    spawned = []
    for i in range(count):
        offset = pygame.Vector2(random.uniform(-800, 800), random.uniform(-800, 800))
        vel = pygame.Vector2(random.uniform(-80, 80),   random.uniform(-80, 80))
        asteroid = Planet(pos + offset, vel, 'moon', random.uniform(2, 5), size=random.uniform(0.05, 0.2))
        active_object.add(asteroid)
        spawned.append(asteroid)
    return spawned


def prefab_black_hole(pos):
    bh = Planet(pos, (0, 0), 'black_hole', density=50, size=0.6)
    active_object.add(bh)

    spawned = [bh]
    ring_count = random.randint(4, 8)
    for i in range(ring_count):
        r = random.uniform(400, 900)
        angle = (360 / ring_count) * i
        debris = spawn_in_orbit(pos, bh.mass, r, angle,'moon', random.uniform(1, 3), random.uniform(0.05, 0.15))
        spawned.append(debris)
    return spawned

def prefab_triple_star(pos):
    p1, p2 = prefab_binary_planet(pos, density1=4, size1=1.2, density2=3.5, size2=1.0, separation=600)
    inner_mass = p1.mass + p2.mass
    r_outer = random.uniform(1500, 2500)
    p3 = spawn_in_orbit(pos, inner_mass, r_outer, 0, random_planet_type(), 3.0, random.uniform(0.8, 1.4))
    return p1, p2, p3

def prefab_ringed_planet(pos):
    central = Planet(pos, (0, 0), random_planet_type(), density=3.5, size=2.0)
    active_object.add(central)
    
    spawned = [central]
    ring_count = random.randint(10, 18)
    for i in range(ring_count):
        angle = (360 / ring_count) * i
        moon = spawn_in_orbit(pos, central.mass, 700, angle,'moon', random.uniform(1, 2), random.uniform(0.05, 0.12))
        spawned.append(moon)
    return spawned

def prefab_satellite_network(pos):
    central = Planet(pos, (0, 0), random_planet_type(), density=3.5, size=1.5)
    active_object.add(central)

    spawned = [central]
    for i in range(random.randint(3, 6)):
        r = random.uniform(350, 900)
        angle = random.uniform(0, 360)
        sat = spawn_in_orbit(pos, central.mass, r, angle,'sattelite', 6.0, random.uniform(0.04, 0.09))
        spawned.append(sat)
    return spawned

def prefab_enemy_patrol(pos):
    # Kies een willekeurig vijandtype, waarbij spawn_weight bepaalt hoe vaak elk type gekozen wordt
    types   = all_enemy_types
    weights = [t.spawn_weight for t in types]
    chosen  = random.choices(types, weights=weights, k=1)[0]

    # Spawn 2 tot 4 vijanden van hetzelfde type, verspreid rond het middelpunt
    spawned = []
    count = random.randint(2, 4)
    for i in range(count):
        offset = pygame.Vector2(random.uniform(-300, 300), random.uniform(-300, 300))
        enemy = chosen(pos=pos + offset)
        active_object.add(enemy)
        spawned.append(enemy)
    return spawned

all_prefabs = {
    'binary':     prefab_binary_planet,
    'moon':       prefab_moon_system,
    'asteroids':  prefab_asteroid_field,
    'black_hole': prefab_black_hole,
    #'triple':     prefab_triple_star, this one is very unstable and should be reworked
    'ringed':     prefab_ringed_planet,
    'satellite':  prefab_satellite_network,
    #'enemies':    prefab_enemy_patrol, we'll rework enemy spawning
}
#%% Main function

def main():
    # Spawn targets éénmalig vóór de loop
    ''' 
     for i in range(3):
         pos = (random.uniform(100, 400), i * 200)
         active_object.append(Target(pos, size=1.5))
     '''
    '''for i in range(20):
        pos = (random.uniform(100, 400), i * 200)
        active_object.append(BaseEnemy(pos,angle = 120))
        
    '''
    if not debug_freecam:
        active_object.add(player)
   
    debug_enemy = BaseEnemy(pos = (800,0), angle = 180)
    active_object.add(debug_enemy)

    active_object.add(debug_mass)
    while True: 
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                raise SystemExit #fix voor macOS
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    simpel_planet_spawn(player.pos,vel = (0,0))
                if event.key == pygame.K_p:
                    prefab_binary_planet(camera.pos)
                if event.key == pygame.K_o:
                    simpel_planet_spawn(camera.pos,vel=(0,0))
                
        
        #update world gen
        chunkmanager.update()
        
        # Beweeg alle objecten
        active_object.update()
        bullets.update()
        
        # Beweeg de camera
        if debug_freecam:
            camera.freecam()
            player.pos = camera.pos
        else:
            camera.track(player)
        
        # Teken alles
        camera.background_draw()
        camera.draw(active_object)
        camera.draw(bullets) 
        camera.player_predict_draw()
        if debug:
            camera.debug_draw(player)
            camera.debug_draw(active_object)
        camera.finalise()
        #print(clock.get_fps())
        pygame.display.update()
        clock.tick(fps)
        

#%% actually what runs 
# try-except prevents kernel crash in case of bug, because pygame needs to quit proper 
pygame.init()
try:
    random.seed(1234)
    info = pygame.display.Info()
    width = int(info.current_w * 0.9)   # 90% of screen width
    height = int(info.current_h * 0.9)  # 90% of screen height


    true_width = 3000 # change to alter game size
    screen = pygame.display.set_mode((width, height), pygame.SCALED) # Fix voor Mac computers met HIDPI-scaling
    screen_rect = screen.get_rect()
    debug = True
    debug_player = False
    debug_planet = False
    debug_freecam = False
    debug_disable_world_gen = False
    debug_world_gen = False
    debug_enemy = True
    
    player = Player((0,0), (0,0), 0)
    camera = Camera(screen)
    clock = pygame.time.Clock()
    fps = 60
    timestep = 1/fps
    grav_cte = 6000
    active_object = ActiveObjects()
    bullets = ActiveObjects()
    chunkmanager = ChunkManager(around_chunks=1, chunk_size  = (5000,5000))
    debug_mass = DebugMass()
    main()

# Fix voor MacOS
except SystemExit:
    pass
except:
    traceback.print_exc()
finally:
    pygame.quit()