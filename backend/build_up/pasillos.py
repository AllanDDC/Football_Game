# backend/build_up/pasillos.py
import math
import random
from .base import EstrategiaOfensiva
from ..config import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS

class EstrategiaPasillos(EstrategiaOfensiva):
    def ejecutar(self, jug, contexto):
        poseedor = contexto.get('poseedor')
        equipo_rival = contexto.get('equipo_rival')
        es_local = contexto.get('es_local', True)

        if poseedor is None or jug.tiene_balon:
            return None

        defensas_rivales = [j for j in equipo_rival.jugadores if 0 < j.numero < 5]
        if not defensas_rivales:
            porteria_x = SCREEN_WIDTH if es_local else 0
            return (porteria_x + random.uniform(-50, 50), SCREEN_HEIGHT/2 + random.uniform(-50, 50))

        # Buscar hueco entre defensas
        defensas_ordenadas = sorted(defensas_rivales, key=lambda j: j.y)
        huecos = []
        for i in range(len(defensas_ordenadas) - 1):
            j1 = defensas_ordenadas[i]
            j2 = defensas_ordenadas[i+1]
            if abs(j1.x - j2.x) < 60:
                hueco_y = (j1.y + j2.y) / 2
                huecos.append((j1.x, hueco_y))

        if huecos:
            hueco = random.choice(huecos)
            destino_x = hueco[0] + random.uniform(-30, 30)
            destino_y = hueco[1] + random.uniform(-30, 30)
        else:
            # espacio entre defensa y mediocampo
            mediocampistas = [j for j in equipo_rival.jugadores if 5 <= j.numero < 9]
            if mediocampistas:
                y_media = sum(j.y for j in mediocampistas) / len(mediocampistas)
                y_defensa = sum(j.y for j in defensas_rivales) / len(defensas_rivales)
                destino_y = (y_defensa + y_media) / 2 + random.uniform(-20, 20)
            else:
                destino_y = sum(j.y for j in defensas_rivales) / len(defensas_rivales) + random.uniform(-30, 30)
            x_def = sum(j.x for j in defensas_rivales) / len(defensas_rivales)
            destino_x = x_def + (50 if es_local else -50) + random.uniform(-20, 20)

        return (destino_x, destino_y)