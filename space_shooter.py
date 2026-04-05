import pygame
import traceback
import random
from sys import exit



#%% classes
class BasicObject():
    def __init__(self,pos:pygame.Vector2 = 0):
        self.pos = pygame.math.Vector2(pos)
    def update(self):
        #these are important to keep the update()-chain from breaking
        pass
    def pre_update(self):
        pass
class VisualObject(BasicObject):
    def __init__(self,image: pygame.Surface, **kwargs):
        if type(image) == str:
            image = pygame.image.load(image).convert_alpha() 
        super().__init__(**kwargs)
        self.image : pygame.Surface = image
        self.base_image = self.image
    
       
    def get_frame_pos(self) -> pygame.Vector2:
        sprite_offset = pygame.math.Vector2(self.image.get_width() // 2, self.image.get_height() // 2)
        return self.pos - sprite_offset
class MovingObject(BasicObject):
    def __init__(self,vel = 0,acc = 0,**kwargs):
        super().__init__(**kwargs)
        self.vel = pygame.Vector2(vel)
        self.acc = pygame.Vector2(acc)
    def update(self):
        # timestep is a global variable linked to framerate
        self.pos += self.vel * timestep + 0.5 * self.acc * timestep ** 2
        self.vel += self.acc * timestep
        super().update()
class GravityObject(BasicObject):
    def __init__(self,mass:int = 200,**kwargs):
        super().__init__(**kwargs)
        if isinstance(self, MovingObject):
            self.force = pygame.Vector2(0)
        self.mass = mass
    def grav_add(self, other: "GravityObject"):
        if self.pos == other.pos or not hasattr(self, 'force'):
            return
        diff = other.pos - self.pos
        diff_mag_sq = diff.magnitude_squared()
        if diff_mag_sq > 6000 ** 2:
            return
        
        epsilon = 50  # tune this - higher = softer gravity at close range, unrealistic but improves controlabilit
        softened_dist_sq = diff.magnitude_squared() + epsilon**2
        f = grav_cte * self.mass * other.mass * diff / softened_dist_sq**1.5
        self.force += f
    def pre_update(self):
        if isinstance(self, MovingObject):
            #active_object is a global
            self.force = pygame.Vector2(0)
            for object in active_object:
                self.grav_add(object)
            if isinstance(self, MovingObject):
                self.acc = self.force / self.mass
        super().pre_update()     
class RotatingObject(BasicObject):
    def __init__(self,angle,angle_moment = 0,**kwargs):
         super().__init__(**kwargs)
         self.angle = angle
         self.angle_moment = angle_moment
    def angle_dampen(self):
        self.angle_moment = pygame.math.clamp(self.angle_moment, -150, 150)
        if self.angle_moment > 0: self.angle_moment -= 2
        if self.angle_moment < 0: self.angle_moment += 2
    def update(self):
        self.angle += self.angle_moment*timestep
        if isinstance(self, VisualObject): self.image = pygame.transform.rotozoom(self.base_image, self.angle, 1)
        super().update()
class Hitbox(BasicObject):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
    def hit(self,other: 'Hitbox') -> bool:
        pass
class CircularHitbox(Hitbox):
    def __init__(self,radius,**kwargs):
        super().__init__(**kwargs)
        self.hitbox_radius = radius
    def hit(self,other)-> bool:
        if isinstance(other, CircularHitbox):
            return (self.pos - other.pos).magnitude_squared() <= (self.hitbox_radius + other.hitbox_radius)**2     
class PhysicsObject(GravityObject,MovingObject,VisualObject,CircularHitbox):
    def __init__(self, pos, image,vel = 0, force = 0, mass = 20, hitbox_radius = 20, **kwargs):
        super().__init__(pos=pos, image=image,vel=vel, mass=mass, radius = hitbox_radius, **kwargs)
        
    
    def elastic_collision(self, other,energy_dis = 1):
         
         if other.pos == self.pos:
             return
         # Normal vector along collision axis
         relative = (other.pos - self.pos)
         normal = relative.normalize()
         overlap = relative.magnitude() - self.hitbox_radius - other.hitbox_radius
     
         # Relative velocity along normal
         rel_vel = self.vel - other.vel
         vel_along_normal = rel_vel.dot(normal)
         
         # Don't resolve if objects are moving apart
         if vel_along_normal < 0:
             return
         
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
    #list to keep all physicsobjects in
    def __init__(self):
        super().__init__()
    def add(self,other:PhysicsObject):
        self.append(other)
    def update(self):
        for e in self:
            e.pre_update() # calculates without action (eg. gravity)
        for e in self:
            e.update() # the action (eg. movement)
class Planet(PhysicsObject):
    def __init__(self, pos, vel, style,density, size = 1):
        image = Planet.get_image(style,size)
        mass = 2500*density * size**2
        super().__init__(pos = pos ,image = image,vel=vel,mass = mass,hitbox_radius=size*255)
    def get_image(style,size):
        if style == 'icy':
            i = random.randint(0, 4)
            
            path = f'graphics/planets/Ice/{i}.png'
        else:
            raise ValueError(f'style:{style} is not supported')
        image = pygame.image.load(path).convert_alpha()
        image = pygame.transform.rotozoom(image, 0, size)
        return image
    
    def resolve_collisions(self):
        for sprite in active_object:
            if id(sprite)< id(self) and self.hit(sprite):
                #id prevents double resolve
                if isinstance(sprite, Planet):
                    self.elastic_collision(sprite,energy_dis= 0.9)
                    
        
    def update(self):
        super().update()
        if isinstance(self,MovingObject):
            self.resolve_collisions()
class Camera(BasicObject):
    #handles drawing and free scrolling screen
    def __init__(self,screen):
        super().__init__()
        self.final_screen = screen
        self.scaler = self.final_screen.get_width()/true_width
        self.pre_screen = pygame.Surface((true_width,self.final_screen.get_height()/self.scaler))
        self.screen_height = self.pre_screen.get_height()
        self.screen_width = self.pre_screen.get_width()
        self.offset = pygame.math.Vector2(self.screen_width / 2, self.screen_height / 2)
        #background
        self.background_surf = pygame.image.load('graphics/background/Starfield_05-1024x1024.png').convert()
        self.background_rect = self.background_surf.get_rect()
        self.background_pos = pygame.Vector2((0,0))
    def track(self,target):
        offset = target.vel.copy()
        max_offset = self.offset - (100,100)
        offset.x = pygame.math.clamp(offset.x, - max_offset.x, max_offset.x)
        offset.y = pygame.math.clamp(offset.y, - max_offset.y, max_offset.y)
        
           # Where we want the camera to be
        desired_pos = target.pos + offset
        
        # Smooth lerp toward desired position
        LERP_SPEED = 0.08  # 0.0 = no movement, 1.0 = instant snap
        
        delta = desired_pos - self.pos
        
        # Soft dead zone — scale down delta when close, don't hard-cut it
        dist = delta.magnitude()
        if dist > 0:
            # Ease out: slow down as we approach target
            ease_factor = min(dist / 200, 1.0)  # 200 = full-speed radius
            self.pos += delta * LERP_SPEED * ease_factor
    def background_draw(self):
        #tiles background 
        
        bg_w = self.background_surf.get_width()
        bg_h = self.background_surf.get_height()
        
        
        # offset into the tile based on camera position
        start_x = -int(self.pos.x % bg_w)
        start_y = -int(self.pos.y % bg_h)
        
        # tile across the full screen
        x = start_x
        while x < self.screen_width:
            y = start_y
            while y < self.screen_height:
                self.pre_screen.blit(self.background_surf, (x, y))
                y += bg_w
            x += bg_h
    def debug_draw(self,group):
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
    def draw(self,group):
        if not hasattr(group,'__iter__'): # catches when attempting to draw a single object
            group = [group]
        for sprite in group:
            pos = sprite.get_frame_pos() - self.pos + self.offset
            self.pre_screen.blit(sprite.image,pos)
    def finalise(self):
        
        self.final_screen.blit(pygame.transform.rotozoom(self.pre_screen, 0, self.scaler),(0,0))
    def freecam(self):
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
class Player(PhysicsObject,RotatingObject):

    def __init__(self, pos, vel, angle):
        super().__init__(pos = pos, image = 'graphics/player/spaceship1.png',vel = vel , mass = 100, angle = angle , hitbox_radius= 15)
        self.base_image = pygame.transform.rotozoom(self.base_image, -90, 0.2)
    def input_check(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            a = pygame.math.Vector2()
            a.from_polar((400, -self.angle))
            if self.vel.dot(a) > 0:                            # check if  the force attempts increase in vel
                vel_norm = self.vel.normalize()
                a_parallel = vel_norm * a.dot(vel_norm)        # component along velocity
                a_perp = a - a_parallel                        # component perpendicular to velocity
                
                speed = self.vel.magnitude()
                dampen = 1 / (1 + speed * 0.02)
                self.acc += a_parallel * dampen + a_perp # only dampen parallel part
            else:
                self.acc += a
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.angle_moment += 20
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.angle_moment += -20
    def collision_check(self):
        for sprite in active_object:
            if self.hit(sprite):
                if isinstance(sprite, Planet):
                    self.elastic_collision(sprite,energy_dis= 1.1)
                    self.vel:pygame.Vector2                  
    def update(self):
        if not debug_freecam: self.input_check()
        self.angle_dampen()
        self.collision_check()
        super().update()
#%% functions
def simpel_planet_spawn(player):
    #temperorary helper for planet tests
    pos = player.pos + pygame.Vector2(random.uniform(400, 800),random.uniform(400, 800))
    vel = pygame.Vector2(random.uniform(-200, 200),random.uniform(-200, 200))
    density = 2.5
    
    active_object.add(Planet(pos,vel,'icy',density,size=random.uniform(0.1,1.5)))
            

#%% main function

def main():
    active_object.add(Planet((1500,0),(0,0),'icy',2.5,size=1.2))
    active_object.add(Planet((2200,0),(0,250),'icy',1.4,size=0.2))
    while True: 
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    simpel_planet_spawn(player)
        
        active_object.update()
        
        if debug_freecam:
            camera.freecam()
        else:
            camera.track(player)
            
        camera.background_draw()
        camera.draw(active_object)
        camera.draw(player)
        if debug:
            camera.debug_draw(player)
            camera.debug_draw(active_object)
        camera.finalise()
        pygame.display.update()
        clock.tick(fps)
#%% actually what runs 
# try-except prevents kernel crash in case of bug, because pygame needs to quit proper 
pygame.init()
try:
    info = pygame.display.Info()
    width = int(info.current_w * 0.9)   # 90% of screen width
    height = int(info.current_h * 0.9)  # 90% of screen height
    true_width = 4000 # change to alter game size
    screen = pygame.display.set_mode((width, height))
    screen_rect = screen.get_rect()
    debug = True
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
    active_object.add(player)
    main()
except:
    traceback.print_exc()
finally:
    pygame.quit()