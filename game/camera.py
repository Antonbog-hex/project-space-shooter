import pygame
from constants import *
from base_classes import *
from physics import *

class Camera(BasicObject):
    # Beheert het scherm: achtergrond, objecten tekenen en vloeiend de speler volgen
    max_width = 5000 # the max width to zoom out to
    min_width = 2000 # the min width to zoom into
    def __init__(self,screen):
        super().__init__()
        
        self.final_screen = screen # what actually gets shown
        
        #achtergrond
        self.background_surf = pygame.image.load('graphics/background/Starfield_05-1024x1024.png').convert()
        self.background_rect = self.background_surf.get_rect()
        self.background_pos = pygame.Vector2((0,0))
        # zooming
        self.zoom_level = 1.0
        self.min_zoom = __class__.min_width / true_width
        self.max_zoom = __class__.max_width / true_width
        self._rebuild_pre_screen()
        # for LERP on predict
        self.prev_pos = None
        
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
        to_fit_vector = last_pred - target.pos
        desired_height = abs(to_fit_vector.y) * 2
        desired_width = abs(to_fit_vector.x)  * 2
        
        base_h = self.final_screen.get_height()
        base_w = self.final_screen.get_width()
          
        required_zoom =  desired_height/base_h 
        required_zoom = max(required_zoom , desired_width/base_w)
        required_zoom = pygame.math.clamp(required_zoom, self.min_zoom, self.max_zoom)
        if abs(required_zoom- self.zoom_level) > 0.01:
            self.zoom_level += (required_zoom - self.zoom_level) * 0.05 # LERP zoom
            self._rebuild_pre_screen()  
    def background_draw(self):
        # Tegelt de achtergrondafbeelding zodat hij oneindig groot lijkt.
        
        bg_w = self.background_surf.get_width()
        bg_h = self.background_surf.get_height()
        
        parralax = 0.9
        
        top_left_x = self.pos.x * parralax - self.offset.x
        top_left_y = self.pos.y * parralax - self.offset.y
        
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
            if sprite._is_physics:
                pos = sprite.pos
                pos = pos - self.pos + self.offset
                a = sprite.acc
                if a.magnitude_squared() != 0: a=a.clamp_magnitude(800)
                pygame.draw.line(self.pre_screen, 'red', pos, pos+a)
                v = sprite.vel
                if v.magnitude_squared() != 0: v=v.clamp_magnitude(800)
                pygame.draw.line(self.pre_screen, 'orange', pos, pos+v)
            else: continue
            if debug_bullets and isinstance(sprite,BaseBullet):
                pygame.draw.circle(self.pre_screen, 'red', pos, sprite.hitbox_radius,width = 1)
                if isinstance(sprite,RocketBullet): pygame.draw.line(self.pre_screen,'white',pos,pos + sprite.current_heading * 100)
            if sprite._is_target:
                pygame.draw.circle(self.pre_screen, 'green', pos, sprite.hitbox_radius,width = 1)
            if sprite._is_enemy and debug_enemy:
                pygame.draw.line(self.pre_screen,'white',pos,pos + sprite.current_heading * 800)
                pygame.draw.circle(self.pre_screen, 'green', pos, sprite.hitbox_radius,width = 1)
                if sprite.desired_heading != None:
                    pygame.draw.line(camera.pre_screen, 'purple', pos, pos + sprite.desired_heading.normalize() * 100)
                if sprite.aim_target != None:
                    target = sprite.aim_target - self.pos + self.offset
                    pygame.draw.circle(self.pre_screen, 'magenta', target , 5)
            if sprite._is_player and debug_player:
                pygame.draw.circle(self.pre_screen, 'blue', pos, sprite.hitbox_radius,width = 1)
            if sprite._is_planet and debug_planet:
                pygame.draw.circle(self.pre_screen, 'green', pos, sprite.hitbox_radius,width = 1)
    def player_predict_draw(self):
        # Tekent de voorspelde baan van de speler als witte stippen
        '''
        for prediction in player.position_estimation:
            pygame.draw.circle(self.pre_screen, 'white', prediction - self.pos + self.offset , 4)
        '''
        if self.prev_pos == None: self.prev_pos = player.position_estimation
        new_pos_l = []
        for i, pos in enumerate(player.position_estimation):
            prev_pos = self.prev_pos[i]
            new_pos = prev_pos + (pos - prev_pos)*0.1
            new_pos_l.append(new_pos)
            pygame.draw.circle(self.pre_screen, 'white', new_pos - self.pos + self.offset , 4)
        self.prev_predict = new_pos_l
        
            
    def draw(self, group):
        if not hasattr(group, '__iter__'):
            group = [group]
        for sprite in group:
            if not sprite._is_visual: continue
            pos = sprite.get_frame_pos() - self.pos + self.offset
            self.pre_screen.blit(sprite.image, pos)
            ''' 
            !!! to be changed with seperate class !!!
            '''
    def draw_enemy_healthbar(self,enemy_list):
        for sprite in enemy_list:
            bar_width  = 40
            bar_height = 5
            center_pos = sprite.pos - self.pos + self.offset
            bg_rect = pygame.Rect(center_pos.x - bar_width // 2, center_pos.y - 22, bar_width, bar_height)
            pygame.draw.rect(self.pre_screen, (150, 0, 0), bg_rect)
            hp_fraction = sprite.hp / sprite.__class__.max_hp
            hp_rect = pygame.Rect(center_pos.x - bar_width // 2, center_pos.y - 22, int(bar_width * hp_fraction), bar_height)
            pygame.draw.rect(self.pre_screen, (0, 200, 0), hp_rect)

    def draw_player_hp(self, player):
        # HP balk linksonder op het echte scherm
        bar_w = 200
        bar_h = 18
        x = 15
        y = self.final_screen.get_height() - 35
        pygame.draw.rect(self.final_screen, (100, 0, 0), (x, y, bar_w, bar_h), border_radius=4)
        fraction = max(0, player.hp / player.max_hp)
        pygame.draw.rect(self.final_screen, (0, 180, 0), (x, y, int(bar_w * fraction), bar_h), border_radius=4) # health
        fraction = max(0, player.shield / player.max_hp)
        pygame.draw.rect(self.final_screen, (40, 183, 235), (x, y, int(bar_w * fraction), bar_h), border_radius=4) # shield
        pygame.draw.rect(self.final_screen, (255, 255, 255),(x, y, bar_w, bar_h), width=1, border_radius=4)
        
    def finalise(self):
        # Schaal de pre_screen naar het echte venster en toon hem
        target_w = int(self.pre_screen.get_width() * self.scaler)
        target_h = int(self.pre_screen.get_height() * self.scaler)
        scaled = pygame.transform.scale(self.pre_screen, (target_w, target_h))
        #scaled = pygame.transform.rotozoom(self.pre_screen, 0, self.scaler)
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