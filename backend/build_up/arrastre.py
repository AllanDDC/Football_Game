# backend/build_up/arrastre.py
import math
import random
from .base import EstrategiaOfensiva
from ..config import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS

class EstrategiaArrastre(EstrategiaOfensiva):
    def ejecutar(self, jug, contexto):
        poseedor = contexto.get('poseedor')
        es_local = contexto.get('es_local', True)

        if poseedor is None or jug.tiene_balon:
            return None

        # Moverse hacia atrás y hacia un lado para arrastrar marca
        if es_local:
            dx = - (40 + random.uniform(0, 30))
            dy = random.uniform(-50, 50)
        else:
            dx = 40 + random.uniform(0, 30)
            dy = random.uniform(-50, 50)

        destino_x = jug.x + dx
        destino_y = jug.y + dy
        return (destino_x, destino_y)