import pygame
import traceback
import random
from sys import exit


pygame.init()
#%% classes
    
class PhysicsObject(pygame.sprite.Sprite):
    #general object that causes and may be subject to gravity
    def __init__(self, pos, image,vel = 0, force = 0, mass = 20, moving = True, hitbox_radius = 20):
        super().__init__()
        self.pos = pygame.math.Vector2(pos)
        self.vel = pygame.math.Vector2(vel)
        self.force = pygame.math.Vector2(force)
        self.mass = mass
        self.is_moving = moving
        
        
        if type(image) == str:
             self.base_image = pygame.image.load(image).convert_alpha()
        else:
            self.base_image = image
        self.image = self.base_image
        self.rect = self.image.get_rect(center=screen_rect.center)
        self.hitbox_radius = hitbox_radius or min(self.rect.x,self.rect.y)

    @property
    def get_frame_pos(self):
        sprite_offset = pygame.math.Vector2(self.image.get_width() // 2, self.image.get_height() // 2)
        return self.pos - sprite_offset

    def grav_add(self, other):
       if self.pos == other.pos:
           return
    
       diff = other.pos - self.pos
       epsilon = 120  # tune this - higher = softer gravity at close range, unrealistic but improves controlabilit
       softened_dist = (diff.magnitude_squared() + epsilon**2) ** 0.5
        
       f = grav_cte * self.mass * other.mass * diff / softened_dist**3
       if self.check_collision(other):
           normal = (self.pos - other.pos).normalize()
           f = f - f.dot(normal) * normal
       
       self.force += f
       

    def physics_sim(self):
        timestep = 1 / fps
        self.pos += self.vel * timestep + 0.5 * self.force / self.mass * timestep**2
        self.vel += self.force / self.mass * timestep
        
       
        
        self.rect.center = self.pos
        
    def update_forces(self,physicsobject_iterable):
        for target in physicsobject_iterable:
            self.grav_add(target)
            
            
            
    def update(self,reset_force = True):
        if self.is_moving:
            if reset_force: self.force.xy = (0, 0)
            self.update_forces(active_physicsobjects)
            self.physics_sim()
    
    def check_collision(self,other):
        if (self.pos - other.pos).magnitude_squared() <= (self.hitbox_radius + other.hitbox_radius) ** 2:
            return True
        return False
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
        if other.is_moving:
            other.vel += impulse * self.mass * normal
            other.pos -= normal*0.51*overlap
        
class Planet(PhysicsObject):
    def __init__(self, pos, vel, style,density, size = 1 ,ismoving = False):
        image = Planet.get_image(style,size)
        mass = 2500*density * size**2
        super().__init__(pos,image,vel=vel,mass = mass,moving= ismoving,hitbox_radius=size*255)
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
        for sprite in active_physicsobjects:
            if sprite is not self and self.check_collision(sprite):
                if isinstance(sprite, Planet):
                    self.elastic_collision(sprite,energy_dis= 0.9)
                    
        
    def update(self):
        super().update()
        if self.is_moving:
            self.resolve_collisions()
class Camera():
    #handles drawing and free scrolling screen
    def __init__(self,screen):
        self.truescreen = screen
        self.scaler = self.truescreen.get_width()/true_width
        self.screen = pygame.Surface((true_width,self.truescreen.get_height()/self.scaler))
        self.screen_height = self.screen.get_height()
        self.screen_width = self.screen.get_width()
        self.pos = pygame.math.Vector2(0,0)
        
        
        self.offset = pygame.math.Vector2(self.screen_width / 2, self.screen_height / 2)
        self.safe_dis = (self.screen_height**2 + self.screen_width**2 ) / 20
        self.max_dis = (max(self.screen_height,self.screen_width)  * 0.9)**2
        
        #background
        self.background_org = pygame.image.load('graphics/background/Starfield_05-1024x1024.png').convert()
        self.background_rect = self.background_org.get_rect()
        self.background_pos = pygame.Vector2((0,0))
    def track(self,target):
        #changes camera pos to target offset makes you look where you will be
        #currently based on vel, could change later
        target = target.sprite
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
        
        bg_w = self.background_org.get_width()
        bg_h = self.background_org.get_height()
        
        
        # offset into the tile based on camera position
        start_x = -int(self.pos.x % bg_w)
        start_y = -int(self.pos.y % bg_h)
        
        # tile across the full screen
        x = start_x
        while x < self.screen_width:
            y = start_y
            while y < self.screen_height:
                self.screen.blit(self.background_org, (x, y))
                y += bg_w
            x += bg_h
        
    def debug_draw(self,group):    
        for sprite in group:
            if isinstance(sprite, Player) and debug_player:
                
                pos = sprite.pos
                pos = pos - self.pos + self.offset
                f = sprite.force
                a = f / sprite.mass
                pygame.draw.line(self.screen, 'red', pos, pos+a)
                v = sprite.vel
                pygame.draw.line(self.screen, 'orange', pos, pos+v)
                pygame.draw.circle(self.screen, 'blue', pos, sprite.hitbox_radius,width = 1)
            if isinstance(sprite, Planet) and debug_planet:
                
                pos = sprite.pos
                pos = pos - self.pos + self.offset
                f = sprite.force
                a = f / sprite.mass
                pygame.draw.line(self.screen, 'red', pos, pos+a)
                v = sprite.vel
                pygame.draw.line(self.screen, 'orange', pos, pos+v)
                pygame.draw.circle(self.screen, 'green', pos, sprite.hitbox_radius,width = 1)
    def draw(self,group):
        for sprite in group:
            
            
            
            
            
           
            pos = sprite.get_frame_pos - self.pos + self.offset
            self.screen.blit(sprite.image,pos)
    def finalise(self):
        
        self.truescreen.blit(pygame.transform.rotozoom(self.screen, 0, self.scaler),(0,0))
    
                
        

class Player(PhysicsObject):
    def __init__(self, pos, vel, force, angle):
        super().__init__(pos, 'graphics/player/spaceship1.png',vel, force,mass=100,hitbox_radius = 12,moving = True)
        self.base_image = pygame.transform.rotozoom(self.base_image, -90, 0.2)
        self.image = self.base_image
        self.rect = self.image.get_rect(center=screen_rect.center)


        self.angle = 0
        self.angle_moment = 0

    def input_check(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            f = pygame.math.Vector2()
            f.from_polar((7000, -self.angle))
            
            if self.vel.dot(f) > 0:                            # check if  the force attempts increase in vel
                vel_norm = self.vel.normalize()
                f_parallel = vel_norm * f.dot(vel_norm)        # component along velocity
                f_perp = f - f_parallel                        # component perpendicular to velocity
                
                speed = self.vel.magnitude()
                dampen = 1 / (1 + speed * 0.003)
                self.force += f_parallel * dampen + f_perp     # only dampen parallel part
            else:
                self.force += f
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            if self.angle_moment < -100: self.angle_moment = -100
            self.angle_moment += 10
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            if self.angle_moment > 100: self.angle_moment = 100
            self.angle_moment += -10


    
    def angle_update(self):
        self.angle = self.angle % 360
        self.angle += self.angle_moment * (1/fps)
        self.angle_moment = pygame.math.clamp(self.angle_moment, -300, 300)
        self.angle_moment *= 0.98
        if self.angle_moment > 0: self.angle_moment -= .2
        if self.angle_moment < 0: self.angle_moment += .2
    def collision_check(self,physicsobject_iterable):
        for sprite in physicsobject_iterable:
            
            if self.check_collision(sprite):
                if isinstance(sprite, Planet):
                    self.elastic_collision(sprite,energy_dis= 0.9)
    def update(self):
        #general update, force reset order is necessary for input
        self.force.xy = (0,0)
        self.input_check()
        self.angle_update()
        super().update(reset_force=False)
        self.collision_check(active_physicsobjects)
        self.image = pygame.transform.rotozoom(self.base_image, self.angle, 1)
        
        

#%% functions


def simpel_planet_spawn(player):
    #temperorary helper for planet tests
    pos = player.pos + pygame.Vector2(random.uniform(400, 800),random.uniform(400, 800))
    vel = pygame.Vector2(random.uniform(-500, 500),random.uniform(-500, 500))
    density = 2.5
    
    active_physicsobjects.add(Planet(pos,vel,'icy',density,size=random.uniform(0.1,1.5),ismoving = True))
            

#%% main stuff
info = pygame.display.Info()
width = int(info.current_w * 0.9)   # 90% of screen width
height = int(info.current_h * 0.9)  # 90% of screen height
true_width = 1500
screen = pygame.display.set_mode((width, height))

screen_rect = screen.get_rect()


debug = True
debug_player = True
debug_planet = True

def main():
    global fps, debug, grav_cte,active_physicsobjects 
    player_group = pygame.sprite.GroupSingle()
    player = Player((0,0), (0,200), (0,0), (0,1))
    player_group.add(player)
    camera = Camera(screen)
    clock = pygame.time.Clock()
    fps = 60
    grav_cte = 6000
    
    active_physicsobjects = pygame.sprite.Group()
    
    
    
    active_physicsobjects.add(Planet((1500,0),(0,0),'icy',2.5,size=1.2,ismoving = False))
    active_physicsobjects.add(Planet((2200,0),(0,400),'icy',1.4,size=0.2,ismoving = True))
    
    
    while True:
        if debug:
            pass
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    simpel_planet_spawn(player)
       
        
       
        player_group.update()
        active_physicsobjects.update()
        camera.track(player_group)
        camera.background_draw()
        
        
        
        camera.draw(active_physicsobjects)
        camera.draw(player_group)
        
        
        if debug:
            camera.debug_draw(player_group)
            camera.debug_draw(active_physicsobjects)
        camera.finalise()
        pygame.display.update()
        clock.tick(fps)
        print(f'fps:{round(clock.get_fps())}', f'current planets: {len(active_physicsobjects)}')
try:
    main()
except:
    traceback.print_exc()
finally:
    pygame.quit()