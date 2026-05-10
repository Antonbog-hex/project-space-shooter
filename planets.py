import pygame
import random
import gamestate as g
from constants import grav_cte
from base_classes import PhysicsObject
from rendering import VisualObject


class Planet(PhysicsObject,VisualObject):
    # Een planeet: heeft een afbeelding, massa (gebaseerd op dichtheid+grootte) en botst elastisch met andere planeten.
    def __init__(self, pos, vel, style,density, size = 1):
        self.style = style
        image = Planet.get_image(style,size)
        mass = 2500*density * size ** 2
        super().__init__(pos = pos ,image = image,vel=vel,mass = mass,hitbox_radius=size*255)
        self._is_planet = True
    
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
        # Controleer botsingen met andere planeten, (id-check voorkomt dubbele afhandeling)
        # spaceship botsingen worden afgehandeld in spaceship
        for planet in g.planets:
            if id(planet)< id(self) and self.hit(planet):
                self.elastic_collision(planet,energy_dis= 0.9)
               
    def pre_update(self):
        if self._is_moving:
            self.resolve_collisions()
        super().pre_update()
    def update(self):
        
        super().update() 
def simpel_planet_spawn(pos,vel= None):
    #temperorary helper for planet tests
    vel = vel or pygame.Vector2(random.uniform(-200, 200),random.uniform(-200, 200))
    density = 2.5
    p = Planet(pos,vel,random_planet_type(),density,size=random.uniform(1,1.5))
    g.active_object.add(p)
    g.planets.add(p)     
def random_planet_type():
    return random.choice(['icy','desert','earth','ocean','tropical'])
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
    
    g.active_object.add(p1)
    g.active_object.add(p2)
    g.planets.add(p1)
    g.planets.add(p2)
    return p1, p2

def spawn_in_orbit(center_pos, anchor_mass, r, angle, style, density, size):
    v = (grav_cte * anchor_mass / r) ** 0.5
    offset = pygame.Vector2(r, 0).rotate(angle)
    vel = pygame.Vector2(v, 0).rotate(angle + 90)
    planet = Planet(center_pos + offset, vel, style, density, size=size)
    g.active_object.add(planet)
    g.planets.add(planet)
    return planet
def prefab_moon_system(pos, moon_count=None):
    central = Planet(pos, (0,0), random_planet_type(), 4.0, size=1.8)
    g.active_object.add(central)
    g.planets.add(central)
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
        g.active_object.add(asteroid)
        g.planets.add(asteroid)
        spawned.append(asteroid)
    return spawned
def prefab_black_hole(pos):
    bh = Planet(pos, (0, 0), 'black_hole', density=50, size=0.6)
    g.active_object.add(bh)
    g.planets.add(bh)
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
    g.active_object.add(central)
    g.planets.add(central)
    
    spawned = [central]
    ring_count = random.randint(10, 18)
    for i in range(ring_count):
        angle = (360 / ring_count) * i
        moon = spawn_in_orbit(pos, central.mass, 700, angle,'moon', random.uniform(1, 2), random.uniform(0.05, 0.12))
        spawned.append(moon)
    return spawned
def prefab_satellite_network(pos):
    central = Planet(pos, (0, 0), random_planet_type(), density=3.5, size=1.5)
    g.active_object.add(central)
    g.planets.add(central)
    spawned = [central]
    for i in range(random.randint(3, 6)):
        r = random.uniform(350, 900)
        angle = random.uniform(0, 360)
        sat = spawn_in_orbit(pos, central.mass, r, angle,'sattelite', 6.0, random.uniform(0.04, 0.09))
        spawned.append(sat)
    return spawned
all_prefabs = {
    'binary':     prefab_binary_planet,
    'moon':       prefab_moon_system,
    'asteroids':  prefab_asteroid_field,
    'black_hole': prefab_black_hole,
    #'triple':     prefab_triple_star, this one is very unstable and should be reworked
    'ringed':     prefab_ringed_planet,
    'satellite':  prefab_satellite_network
}
