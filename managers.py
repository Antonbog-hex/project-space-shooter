import pygame
import random
import gamestate as g
from constants import debug_disable_world_gen,debug_disable_enemy_spawn
from base_classes import PhysicsObject
from physics import Predictor
from spaceships import Spaceship
from enemies import all_enemy_types
from planets import all_prefabs


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
                g.active_object.add(element)
                if element._is_planet: g.planets.add(element)
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
        
        delta = pygame.Vector2(random.uniform(-random_pos, random_pos),random.uniform(-random_pos, random_pos))
        g.enemy_manager.spawn_seq(chunk_center+delta)
            
    def update(self):
        self.central_chunk = self.get_chunk(g.player.pos)
        self.active_chunk_update()
        self.calculate_safezone()
class EnemyManager:
    min_spawn_dist = 3000
    max_spawn_dist = 8000
    max_enemies = 30
    spawn_ticks = 300 # number of ticks between enemy spawns at difficulty 1
    def __init__(self):
        self.all_enemies = all_enemy_types
        self.weights = [t.spawn_weight for t in self.all_enemies]
        self.spawn_ticker = self.__class__.spawn_ticks
        self.difficulty_score = 1 # larger = more difficult
    def spawn_enemy(self,enemy_type,pos):
        if debug_disable_enemy_spawn: return
        enemy = enemy_type(pos)
        g.active_object.add(enemy)
        g.enemies.add(enemy)
    def get_enemy_type(self):
        return random.choices(self.all_enemies, weights=self.weights, k=1)[0]
    def find_spot(self,pos:pygame.Vector2, min_dist = None, max_dist =None):
        max_dist = max_dist or self.__class__.max_spawn_dist
        min_dist = min_dist or self.__class__.min_spawn_dist
        dist = random.uniform(min_dist,max_dist)
        angle = random.uniform(0,360)
        delta = pygame.Vector2.from_polar((dist,angle))
        pos = pygame.Vector2(pos) + delta
        tester = Predictor(pos, mass = Spaceship.standard_mass)
        for i in range(5):
            tester.pre_update()
            f = tester.force
            if f.magnitude_squared() < 2000 ** 2 and (pos-g.player.pos).magnitude_squared() > self.__class__.min_spawn_dist ** 2:
                return pos
            f += pygame.Vector2(0.1,0.1)
            tester.pos -= 10* f / (f*f) ** 0.25
        return None
    def spawn_seq(self,start_pos):
        if debug_disable_enemy_spawn: return
        pos = self.find_spot(start_pos)
        enemy_type = self.get_enemy_type()
        if pos == None: return
        self.spawn_enemy(enemy_type, pos)
    def update(self):
        if len(g.enemies) >= self.__class__.max_enemies: return
        if self.spawn_ticker <= 0:
            self.spawn_seq(g.player.pos)
            self.spawn_ticker = self.__class__.spawn_ticks
        else:
            self.spawn_ticker -= self.difficulty_score
        if random.randint(0,7200) < self.difficulty_score:
            for enemy in g.enemies:
                enemy.player_memory = enemy.__class__.player_max_memory
class ScoreManager:
    def __init__(self):
        self.score = 0
        self.high_score = 0
        self.font = pygame.font.SysFont('Arial', 28)
        self.small_font = pygame.font.SysFont('Arial', 18)

    def add_score(self, amount):
        self.score += amount
        if self.score > self.high_score:
            self.high_score = self.score
        g.enemy_manager.difficulty_score = self.score // 100 + 1

    def reset(self):
        self.score = 0

    def draw(self, screen):
        score = self.font.render(f'Score: {self.score}', True, (255, 255, 255))
        best_score = self.small_font.render(f'Beste: {self.high_score}', True, (180, 180, 180))
        screen.blit(score, (15, 15))
        screen.blit(best_score, (15, 50))           
class Menu:
    def __init__(self, screen):
        self.screen = screen
        self.font_big = pygame.font.SysFont('Arial', 64, bold=True)
        self.font_med = pygame.font.SysFont('Arial', 36)
        self.font_small = pygame.font.SysFont('Arial', 24)
        self.active = True # True = menu wordt getoond
        self.is_death_screen = False

    def draw(self, high_score=0, last_score=0):
        overlay = pygame.Surface(self.screen.get_size()).convert_alpha()
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        if self.is_death_screen:
            title = self.font_big.render('GAME OVER', True, (220, 60, 60))
            score_line = self.font_med.render(f'Score: {last_score}', True, (255, 255, 255))
            hi_line = self.font_med.render(f'Beste:  {high_score}', True, (180, 180, 180))
            prompt = self.font_small.render('Druk ENTER om opnieuw te spelen | ESC om te stoppen', True, (200, 200, 200))
        else:
            title  = self.font_big.render('SPACE GAME', True, (100, 180, 255))
            score_line = self.font_med.render('', True, (0,0,0))      # leeg
            hi_line    = self.font_med.render(f'Best:  {high_score}', True, (180, 180, 180))
            prompt     = self.font_small.render('Druk ENTER om te starten | ESC om te stoppen', True, (200, 200, 200))

        center_x = self.screen.get_width() // 2
        center_y = self.screen.get_height() // 2

        self.screen.blit(title, title.get_rect(center=(center_x, center_y - 120)))
        self.screen.blit(score_line, score_line.get_rect(center=(center_x, center_y - 30)))
        self.screen.blit(hi_line, hi_line.get_rect(center=(center_x, center_y + 20)))
        self.screen.blit(prompt, prompt.get_rect(center=(center_x, center_y + 100)))
class ActiveObjects(list):
    # Lijst van alle actieve PhysicsObjects. Roept elke frame pre_update() en update() aan op elk object.

    def __init__(self):
        super().__init__()
        self._pending_add = []
    def resolve_pending_add(self):
        for obj in self._pending_add:
            self.append(obj)
        self._pending_add.clear()
    def add(self,other:PhysicsObject):
        self._pending_add.append(other)
    def reset(self):
        self._pending_add.clear()
        self.clear()
    def update(self):
        for e in self:
            e.pre_update() # calculates without action (eg. gravity)
        for e in self:
            e.update() # the action (eg. movement)
        self.resolve_pending_add()