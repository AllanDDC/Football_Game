# backend/build_up/triangulacion.py
import math
import random
from .base import EstrategiaOfensiva
from ..config import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS
from ..physics import distancia_objetos

class EstrategiaTriangulacion(EstrategiaOfensiva):
    def ejecutar(self, jug, contexto):
        poseedor = contexto.get('poseedor')
        equipo = contexto.get('equipo')
        es_local = contexto.get('es_local', True)

        if poseedor is None or jug.tiene_balon:
            return None

        # Buscar compañero para triángulo
        mejores = []
        for comp in equipo.jugadores:
            if comp == jug or comp == poseedor or comp.tiene_balon:
                continue
            dist_comp = distancia_objetos(poseedor, comp)
            if 50 < dist_comp < 200:
                mejores.append(comp)
        if not mejores:
            return None

        companero = random.choice(mejores)

        # Calcular vértice: punto medio desplazado perpendicularmente
        mx = (jug.x + companero.x) / 2
        my = (jug.y + companero.y) / 2
        ux = jug.x - companero.x
        uy = jug.y - companero.y
        norm = math.hypot(ux, uy)
        if norm == 0:
            return None
        ux /= norm
        uy /= norm

        # Perpendicular
        px = -uy
        py = ux

        # Elegir dirección hacia portería
        porteria_x = SCREEN_WIDTH if es_local else 0
        porteria_y = SCREEN_HEIGHT / 2
        ang_perp = math.atan2(py, px)
        ang_porteria = math.atan2(porteria_y - poseedor.y, porteria_x - poseedor.x)
        diff1 = abs(ang_perp - ang_porteria)
        diff2 = abs(ang_perp + math.pi - ang_porteria)
        if diff2 < diff1:
            px = -px
            py = -py

        distancia_vertice = math.hypot(mx - poseedor.x, my - poseedor.y) * 1.2 + 20
        destino_x = poseedor.x + px * distancia_vertice
        destino_y = poseedor.y + py * distancia_vertice

        # Limitar
        destino_x = max(PLAYER_RADIUS, min(SCREEN_WIDTH - PLAYER_RADIUS, destino_x))
        destino_y = max(PLAYER_RADIUS, min(SCREEN_HEIGHT - PLAYER_RADIUS, destino_y))

        return (destino_x, destino_y)