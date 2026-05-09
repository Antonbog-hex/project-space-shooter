import pygame
import random
from constants import *
from base_classes import *

class Predictor(PhysicsObject):
    grav_ticker = 1
    def pre_update(self):
        GravityObject.pre_update(self)
    
    def update(self):
        for obj in active_object:
            if self.hit(obj) and obj._is_physics and obj._is_item:
                self.elastic_collision(obj,energy_dis=1.1,reflective=False)
        super().update()
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

