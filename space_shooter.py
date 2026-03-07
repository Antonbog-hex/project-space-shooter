import pygame
import traceback
import random
from sys import exit


pygame.init()
#%% classes
    
class PhysicsObject(pygame.sprite.Sprite):
    #general object that causes and may be subject to gravity
    def __init__(self, pos, image_path,vel = 0, force = 0, mass = 20, moving = True):
        super().__init__()
        self.pos = pygame.math.Vector2(pos)
        self.vel = pygame.math.Vector2(vel)
        self.force = pygame.math.Vector2(force)
        self.mass = mass
        self.is_moving = moving

        self.base_image = pygame.image.load(image_path).convert_alpha()
        self.image = self.base_image
        self.rect = self.image.get_rect(center=screen_rect.center)

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

class Planet(PhysicsObject):
    def __init__(self, pos, vel, style,mass, ismoving):
        image_path = Planet.get_image(style)
        super().__init__(pos,image_path,mass = mass,moving= ismoving)
    def get_image(style):
        if style == 'icy':
            i = random.randint(0, 4)
            
            return f'graphics/planets/Ice/{i}.png'
        else:
            raise ValueError(f'style:{style} is not supported')

class Camera():
    #handles drawing and free scrolling screen
    def __init__(self,screen):
        self.screen = screen
        self.screen_height = screen.get_height()
        self.screen_width = screen.get_width()
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
        
        self.pos = target.pos + offset
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
        
        
        
    def draw(self,group):
        for sprite in group:
            
            
            
            
            if isinstance(sprite, Player) and debug:
                #this is debug for velocity and force vectors on player
                pos = pygame.math.Vector2(sprite.rect.centerx,sprite.rect.centery)
                pos = pos - self.pos + self.offset
                f = sprite.force
                pygame.draw.line(screen, 'red', pos, pos+f)
                v = sprite.vel
                pygame.draw.line(screen, 'orange', pos, pos+v)
                pygame.draw.circle(screen, 'blue', self.offset, 5)
           
            pos = sprite.get_frame_pos - self.pos + self.offset
            self.screen.blit(sprite.image,pos)
    
                
        

class Player(PhysicsObject):
    def __init__(self, pos, vel, force, angle):
        super().__init__(pos, 'graphics/player/spaceship1.png',vel, force,moving = True)
        self.base_image = pygame.transform.rotozoom(self.base_image, -90, 0.2)
        self.image = self.base_image
        self.rect = self.image.get_rect(center=screen_rect.center)

        self.angle = 0
        self.angle_moment = 0

    def input_check(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            f = pygame.math.Vector2()
            f.from_polar((3000, -self.angle))
            
            if self.vel.dot(f) > 0:
                vel_norm = self.vel.normalize()
                f_parallel = vel_norm * f.dot(vel_norm)        # component along velocity
                f_perp = f - f_parallel                        # component perpendicular to velocity
                
                speed = self.vel.magnitude()
                dampen = 1 / (1 + speed * 0.005)
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

    def update(self):
        #general update, force reset order is necessary for input
        self.force.xy = (0,0)
        self.input_check()
        self.angle_update()
        super().update(reset_force=False)
        self.image = pygame.transform.rotozoom(self.base_image, self.angle, 1)
        
        

#%% functions


def simpel_planet_spawn(player):
    #temperorary helper for planet tests
    pos = player.pos + pygame.Vector2(random.uniform(400, 800),random.uniform(400, 800))
    mass = random.uniform(6200, 10000)
    
    active_physicsobjects.add(Planet(pos,0,'icy',mass,False))
            

#%% main stuff

screen = pygame.display.set_mode((0,0),pygame.FULLSCREEN)
screen_rect = screen.get_rect()




def main():
    global fps, debug, grav_cte,active_physicsobjects
    player_group = pygame.sprite.GroupSingle()
    player = Player((0,0), (0,0), (0,0), (0,1))
    player_group.add(player)
    camera = Camera(screen)
    clock = pygame.time.Clock()
    fps = 60
    grav_cte = 5000
    active_physicsobjects = pygame.sprite.Group()
    active_physicsobjects.add(player)
    debug = False
    
    
    while True:
        
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    simpel_planet_spawn(player)
       
        
       
        player.update()
        camera.track(player_group)
        camera.background_draw()
        
        camera.draw(active_physicsobjects)
        

        pygame.display.update()
        clock.tick(fps)

try:
    main()
except:
    traceback.print_exc()
finally:
    pygame.quit()