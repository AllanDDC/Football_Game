# backend/build_up/bandas.py
import math
import random
from .base import EstrategiaOfensiva
from ..config import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS

class EstrategiaBandas(EstrategiaOfensiva):
    def ejecutar(self, jug, contexto):
        poseedor = contexto.get('poseedor')
        es_local = contexto.get('es_local', True)

        if poseedor is None or jug.tiene_balon:
            return None

        # Decidir banda: si está más cerca de una banda, esa; si no, aleatoria
        if jug.x < SCREEN_WIDTH * 0.3:
            banda = 'izquierda'
        elif jug.x > SCREEN_WIDTH * 0.7:
            banda = 'derecha'
        else:
            banda = 'derecha' if random.random() < 0.5 else 'izquierda'

        # Profundidad según posición del poseedor
        if es_local:
            if poseedor.x < SCREEN_WIDTH * 0.3:
                profundidad = 0.7 + random.uniform(0, 0.2)
            elif poseedor.x < SCREEN_WIDTH * 0.6:
                profundidad = 0.5 + random.uniform(0, 0.2)
            else:
                profundidad = 0.3 + random.uniform(0, 0.2)
        else:
            if poseedor.x > SCREEN_WIDTH * 0.7:
                profundidad = 0.7 + random.uniform(0, 0.2)
            elif poseedor.x > SCREEN_WIDTH * 0.4:
                profundidad = 0.5 + random.uniform(0, 0.2)
            else:
                profundidad = 0.3 + random.uniform(0, 0.2)

        # Ajuste por rol
        if jug.numero < 5:
            profundidad *= 0.6
        elif jug.numero < 9:
            profundidad *= 0.8

        # X en la banda
        if banda == 'izquierda':
            x = PLAYER_RADIUS + 30 + random.uniform(-10, 10)
        else:
            x = SCREEN_WIDTH - PLAYER_RADIUS - 30 + random.uniform(-10, 10)

        # Y según poseedor
        if poseedor:
            angulo = math.atan2(poseedor.y - jug.y, poseedor.x - jug.x)
            y = jug.y + math.sin(angulo) * 100 * profundidad
        else:
            y = SCREEN_HEIGHT / 2 + random.uniform(-50, 50)

        y = max(SCREEN_HEIGHT * 0.1, min(SCREEN_HEIGHT * 0.9, y))
        return (x, y)