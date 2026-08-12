# backend/build_up/avance_vertical.py
import math
import random
from .base import EstrategiaOfensiva
from ..config import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS

class EstrategiaAvanceVertical(EstrategiaOfensiva):
    def ejecutar(self, jug, contexto):
        poseedor = contexto.get('poseedor')
        equipo_rival = contexto.get('equipo_rival')
        es_local = contexto.get('es_local', True)

        if poseedor is None or jug.tiene_balon:
            return None

        porteria_x = SCREEN_WIDTH if es_local else 0
        porteria_y = SCREEN_HEIGHT / 2

        defensas_rivales = [j for j in equipo_rival.jugadores if 0 < j.numero < 5]
        if not defensas_rivales:
            return (porteria_x + random.uniform(-50, 50), porteria_y + random.uniform(-50, 50))

        if es_local:
            ultimo_defensor = max(defensas_rivales, key=lambda j: j.x)
            destino_x = ultimo_defensor.x + random.uniform(30, 80)
        else:
            ultimo_defensor = min(defensas_rivales, key=lambda j: j.x)
            destino_x = ultimo_defensor.x - random.uniform(30, 80)

        # Buscar hueco vertical
        defensas_ordenadas = sorted(defensas_rivales, key=lambda j: j.y)
        espacios = []
        for i in range(len(defensas_ordenadas) - 1):
            j1 = defensas_ordenadas[i]
            j2 = defensas_ordenadas[i+1]
            if j2.y - j1.y > 50:
                espacios.append((j1.y + j2.y) / 2)
        if espacios:
            destino_y = random.choice(espacios) + random.uniform(-20, 20)
        else:
            destino_y = porteria_y + random.uniform(-60, 60)

        # Limitar
        if es_local:
            destino_x = min(SCREEN_WIDTH - 30, destino_x)
        else:
            destino_x = max(30, destino_x)
        destino_y = max(SCREEN_HEIGHT * 0.1, min(SCREEN_HEIGHT * 0.9, destino_y))

        # Si es defensa, no subir tanto
        if jug.numero < 5:
            if es_local:
                destino_x = min(destino_x, jug.x + 100)
            else:
                destino_x = max(destino_x, jug.x - 100)

        return (destino_x, destino_y)