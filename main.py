import pygame
import random
import math
import traceback
from constants import *
from base_classes import *
from physics import *
from effects import *
from bullets import *
from spaceships import *
from planets import *
from items import *
from managers import *

class DebugMass(PhysicsObject,VisualObject):
    def __init__(self):
        image = pygame.Surface((20,20))
        pygame.draw.circle(image,'red',(10,10),10)
        super().__init__((50,50),mass = 300,image=image .convert_alpha())
    def update(self):
        if pygame.mouse.get_pressed()[0]:
            self.mass = 1000
            mouse_screen = pygame.Vector2(pygame.mouse.get_pos())
            mouse_pre = mouse_screen / camera.scaler
            mouse_world = mouse_pre - camera.offset + camera.pos
            self.pos = mouse_world
            self.vel = pygame.Vector2(0)
        else:
            self.mass = 0.01
            self.vel = pygame.Vector2(0)
        super().update()

class Target(PhysicsObject, VisualObject):
    def __init__(self, pos, vel=(0, 0), size=1.0):
        pixel_size = int(60 * size)   
        hitbox = int(30 * size)
        target_surface = pygame.Surface((pixel_size, pixel_size), pygame.SRCALPHA)
        pygame.draw.rect(target_surface, (220, 50, 50), (0, 0, pixel_size, pixel_size), border_radius=6)
        pygame.draw.rect(target_surface, (255, 100, 100), (0, 0, pixel_size, pixel_size), width=2, border_radius=6)
        super().__init__(pos=pos, vel=vel, mass=10, hitbox_radius=hitbox, image=target_surface)
    
    def update(self):
        super().update()

def signed_angle_to(v1, v2):
    cross = -(v1.x * v2.y - v1.y * v2.x)
    dot = v1.dot(v2)
    return math.degrees(math.atan2(cross, dot))

def empty_bin(waste_bin):
    for obj in waste_bin:
        try: active_object.remove(obj)
        except: pass
        try: bullets.remove(obj)
        except: pass
        try: planets.remove(obj)
        except: pass
        try: enemies.remove(obj)
        except: pass
        try: particle_effects.remove(obj)
        except: pass
    waste_bin.clear()

def reset_game():
    global player, active_object, bullets, planets, enemies, chunkmanager, enemy_manager
    active_object.clear()
    bullets.reset()
    planets.reset()
    enemies.reset()
    particle_effects.reset()
    chunkmanager  = ChunkManager(around_chunks=1, chunk_size=(5000, 5000))
    enemy_manager = EnemyManager()
    player        = Player(pos=(0, 0), vel=(0, 200), angle=0)
    score_manager.reset()
    active_object.add(player)
    active_object.add(debug_mass)
    camera.pos = pygame.Vector2(0, 0)
    camera.zoom(1.0)
    camera.prev_pos = None

def main():
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if menu.active:
                        pygame.quit()
                        raise SystemExit
                    else:
                        menu.active = True
                        menu.is_death_screen = False
                if event.key == pygame.K_RETURN:
                    if menu.active:
                        menu.active = False
                        reset_game()

        if menu.active:
            camera.background_draw()
            camera.finalise()
            menu.draw(high_score=score_manager.high_score, last_score=score_manager.score)
            pygame.display.update()
            clock.tick(fps)
            continue
        
        chunkmanager.update()
        enemy_manager.update()
        active_object.update()
        bullets.update()
        enemies.resolve_pending_add()
        planets.resolve_pending_add()
        particle_effects.update()
        
        if debug_freecam:
            camera.freecam()
            player.pos = camera.pos
        else:
            camera.track(player)
    
        camera.background_draw()
        camera.draw(particle_effects)
        camera.draw(active_object)
        camera.draw(bullets)
        camera.draw_enemy_healthbar(enemies)
        camera.player_predict_draw()
        if debug:
            camera.debug_draw(active_object)
            if debug_bullets: camera.debug_draw(bullets)
        camera.finalise()
        score_manager.draw(camera.final_screen)
        camera.draw_player_hp(player)
        if not menu.active:
            camera.draw_player_hp(player)
        empty_bin(waste_bin)
        pygame.display.update()
        clock.tick(fps)

pygame.init()
try:
    init_textures()

    info = pygame.display.Info()
    width = int(info.current_w * 0.9)
    height = int(info.current_h * 0.9)

    screen = pygame.display.set_mode((width, height), pygame.SCALED)
    screen_rect = screen.get_rect()

    player = Player(pos=(0,0), vel=(0,200), angle=0)
    camera = Camera(screen)
    clock = pygame.time.Clock()
    active_object = ActiveObjects()
    bullets = ActiveObjects()
    planets = ActiveObjects()
    enemies = ActiveObjects()
    particle_effects = ActiveObjects()
    chunkmanager = ChunkManager(around_chunks=1, chunk_size=(5000,5000))
    enemy_manager = EnemyManager()
    score_manager = ScoreManager()
    menu = Menu(screen)
    debug_mass = DebugMass()
    main()

except SystemExit:
    pass
except:
    traceback.print_exc()
finally:
    pygame.quit()