# backend/tactics/tiki_taka.py
"""
Táctica Tiki-taka: posesión, pases cortos, presión tras pérdida.
"""

import math
from .base import TacticaBase, _posicion_base, _get_velocidad_efectiva
from ..physics import mover_hacia, distancia_objetos
from ..config import PLAYER_SPEED, SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS


class TikiTaka(TacticaBase):
    def __init__(self):
        params = {
            "profundidad_defensiva": 0.3,
            "distancia_presion": 150,
            "ancho": 0.6,
            "altura_delanteros_defensiva": 0.2,
            "presion_alta": 0.8,
            "velocidad_ataque": 0.4,
            "regate_frecuencia": 0.6,
            "pase_largo": 0.1,
        }
        super().__init__("Tiki-taka", params)

    def actualizar_defensa(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        es_local = equipo.es_local
        profundidad = self.params["profundidad_defensiva"]
        distancia_presion = self.params["distancia_presion"]

        poseedor = None
        if jugador_con_balon is not None and jugador_con_balon.equipo != equipo.nombre:
            poseedor = jugador_con_balon

        for i in range(1, 5):
            jug = equipo.jugadores[i]
            if jug.es_controlado or hasattr(jug, 'expulsado') or hasattr(jug, 'lesionado'):
                continue

            velocidad_base = _get_velocidad_efectiva(jug, factor=0.5)
            bx, by = _posicion_base(i, es_local)

            # Defensa adelantada
            porteria_x = 50 if es_local else SCREEN_WIDTH - 50
            if es_local:
                bx = porteria_x + (bx - porteria_x) * (1 - profundidad * 0.5)
            else:
                bx = porteria_x - (porteria_x - bx) * (1 - profundidad * 0.5)

            if poseedor is not None:
                dist = distancia_objetos(jug, poseedor)
                if dist < distancia_presion:
                    vx, vy = mover_hacia(jug, poseedor, velocidad_base * 1.1, dt)
                    jug.establecer_velocidad(vx, vy)
                    jug.actualizar(dt)
                    continue

            destino = type('obj', (object,), {'x': bx, 'y': by})()
            if distancia_objetos(jug, destino) > 10:
                vx, vy = mover_hacia(jug, destino, velocidad_base * 0.7, dt)
                jug.establecer_velocidad(vx, vy)
                jug.actualizar(dt)
            else:
                jug.establecer_velocidad(0, 0)
                jug.actualizar(dt)

    def actualizar_mediocampistas(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        es_local = equipo.es_local
        poseedor = None
        if jugador_con_balon is not None and jugador_con_balon.equipo != equipo.nombre:
            poseedor = jugador_con_balon

        for i in range(5, 9):
            jug = equipo.jugadores[i]
            if jug.es_controlado or hasattr(jug, 'expulsado') or hasattr(jug, 'lesionado'):
                continue

            velocidad_base = _get_velocidad_efectiva(jug, factor=0.6)
            bx, by = _posicion_base(i, es_local)

            if poseedor is not None:
                dist = distancia_objetos(jug, poseedor)
                if dist < 180:
                    vx, vy = mover_hacia(jug, poseedor, velocidad_base * 0.9, dt)
                    jug.establecer_velocidad(vx, vy)
                    jug.actualizar(dt)
                    continue

            destino = type('obj', (object,), {'x': bx, 'y': by})()
            if distancia_objetos(jug, destino) > 15:
                vx, vy = mover_hacia(jug, destino, velocidad_base * 0.6, dt)
                jug.establecer_velocidad(vx, vy)
                jug.actualizar(dt)
            else:
                jug.establecer_velocidad(0, 0)
                jug.actualizar(dt)

    def actualizar_delanteros(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        es_local = equipo.es_local
        poseedor = None
        if jugador_con_balon is not None and jugador_con_balon.equipo != equipo.nombre:
            poseedor = jugador_con_balon

        for i in range(9, 11):
            jug = equipo.jugadores[i]
            if jug.es_controlado or hasattr(jug, 'expulsado') or hasattr(jug, 'lesionado'):
                continue

            velocidad_base = _get_velocidad_efectiva(jug, factor=0.7)
            porteria_x = SCREEN_WIDTH if es_local else 0
            porteria_y = SCREEN_HEIGHT // 2

            if poseedor is not None:
                # Presión alta
                dist = distancia_objetos(jug, poseedor)
                if dist < 150:
                    vx, vy = mover_hacia(jug, poseedor, velocidad_base * 1.0, dt)
                    jug.establecer_velocidad(vx, vy)
                    jug.actualizar(dt)
                    continue

            # Mantenerse en zona ofensiva
            angulo = math.sin(jug.numero * 1.5) * 1.2
            radio = 70 + (i - 9) * 20
            destino_x = porteria_x + math.cos(angulo) * radio
            destino_y = porteria_y + math.sin(angulo) * radio
            destino = type('obj', (object,), {'x': destino_x, 'y': destino_y})()
            if distancia_objetos(jug, destino) > 15:
                vx, vy = mover_hacia(jug, destino, velocidad_base * 0.6, dt)
                jug.establecer_velocidad(vx, vy)
                jug.actualizar(dt)
            else:
                jug.establecer_velocidad(0, 0)
                jug.actualizar(dt)