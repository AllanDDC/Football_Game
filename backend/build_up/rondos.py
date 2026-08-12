# backend/build_up/rondos.py
import math
import random
from .base import EstrategiaOfensiva
from ..config import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS
from ..physics import distancia_objetos

class EstrategiaRondos(EstrategiaOfensiva):
    def ejecutar(self, jug, contexto):
        poseedor = contexto.get('poseedor')
        equipo = contexto.get('equipo')

        if poseedor is None or jug.tiene_balon:
            return None

        dist_poseedor = distancia_objetos(jug, poseedor)
        if dist_poseedor > 300:
            return None

        radio = 80 + random.uniform(0, 40)
        angulo_actual = math.atan2(jug.y - poseedor.y, jug.x - poseedor.x)
        incremento = (1.0 + random.uniform(-0.5, 1.0)) * 0.8 * 0.016  # dt aprox
        nuevo_angulo = angulo_actual + incremento

        destino_x = poseedor.x + math.cos(nuevo_angulo) * radio
        destino_y = poseedor.y + math.sin(nuevo_angulo) * radio

        # Evitar colisiones
        for comp in equipo.jugadores:
            if comp == jug or comp == poseedor:
                continue
            if distancia_objetos(jug, comp) < 30:
                radio += 20
                destino_x = poseedor.x + math.cos(nuevo_angulo) * radio
                destino_y = poseedor.y + math.sin(nuevo_angulo) * radio
                break

        return (destino_x, destino_y)