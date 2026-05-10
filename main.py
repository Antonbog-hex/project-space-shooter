import pygame
import traceback
import gamestate as g
from rendering import Camera
from player import Player
from managers import ActiveObjects, ChunkManager, EnemyManager, ScoreManager, Menu

def empty_bin(waste_bin):
    for obj in waste_bin:
        try: g.d.remove(obj)
        except: pass
        try: g.bullets.remove(obj)
        except: pass
        try: g.planets.remove(obj)
        except: pass
        try: g.enemies.remove(obj)
        except: pass
        try: g.particle_effects.remove(obj)
        except: pass
    g.waste_bin.clear()

def reset_game():
    #global g.player, g.active_object, bullets, planets, enemies, chunkmanager, enemy_manager
    g.active_object.clear()
    g.bullets.reset()
    g.planets.reset()
    g.enemies.reset()
    g.particle_effects.reset()
    g.chunkmanager  = ChunkManager(around_chunks=1, chunk_size=(5000, 5000))
    g.enemy_manager = EnemyManager()
    g.player        = Player(pos=(0, 0), vel=(0, 200), angle=0)
    g.score_manager.reset()
    g.active_object.add(g.player)
    g.camera.pos = pygame.Vector2(0, 0)
    g.camera.zoom(1.0)
    g.camera.prev_pos = None


def main():
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if g.menu.active:
                        pygame.quit()
                        raise SystemExit
                    else:
                        g.menu.active = True
                        g.menu.is_death_screen = False
                if event.key == pygame.K_RETURN:
                    if g.menu.active:
                        g.menu.active = False
                        reset_game()

        if g.menu.active:
            g.camera.background_draw()
            g.camera.finalise()
            g.menu.draw(high_score=g.score_manager.high_score, last_score=g.score_manager.score)
            pygame.display.update()
            clock.tick(g.fps)
            continue
        
        g.chunkmanager.update()
        g.enemy_manager.update()
        g.active_object.update()
        g.bullets.update()
        g.enemies.resolve_pending_add()
        g.planets.resolve_pending_add()
        g.particle_effects.update()
        
        if g.debug_freecam:
            g.camera.freecam()
            g.player.pos = g.camera.pos
        else:
            g.camera.track(g.player)
    
        g.camera.background_draw()
        g.camera.draw(g.particle_effects)
        g.camera.draw(g.active_object)
        g.camera.draw(g.bullets)
        g.camera.draw_enemy_healthbar(g.enemies)
        g.camera.player_predict_draw()
        if g.debug:
            g.camera.debug_draw(g.active_object)
            if g.debug_bullets: g.camera.debug_draw(g.bullets)
        g.camera.finalise()
        g.score_manager.draw(g.camera.final_screen)
        g.camera.draw_player_hp(g.player)
        if not g.menu.active:
            g.camera.draw_player_hp(g.player)
        empty_bin(g.waste_bin)
        pygame.display.update()
        clock.tick(g.fps)

pygame.init()
try:
    #init_textures()

    info = pygame.display.Info()
    width = int(info.current_w * 0.9)
    height = int(info.current_h * 0.9)

    screen = pygame.display.set_mode((width, height), pygame.SCALED)

    g.player = Player(pos=(0,0), vel=(0,200), angle=0)
    g.camera = Camera(screen)
    clock = pygame.time.Clock()
    g.active_object = ActiveObjects()
    g.bullets = ActiveObjects()
    g.planets = ActiveObjects()
    g.enemies = ActiveObjects()
    g.particle_effects = ActiveObjects()
    g.chunkmanager = ChunkManager(around_chunks=1, chunk_size=(5000,5000))
    g.enemy_manager = EnemyManager()
    g.score_manager = ScoreManager()
    g.menu = Menu(screen)
    main()

except SystemExit:
    pass
except:
    traceback.print_exc()
finally:
    pygame.quit()