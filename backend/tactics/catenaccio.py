# backend/tactics/catenaccio.py
"""
Táctica ultradefensiva: repliegue en bloque, presión solo del más cercano,
los demás cubren espacios y cierran pasillos.
"""

import math
from .base import TacticaBase
from ..physics import mover_hacia, distancia_objetos
from ..config import PLAYER_SPEED, SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS


class Catenaccio(TacticaBase):
    """
    Implementación de Catenaccio: defensa profunda y presión selectiva.
    """

    def __init__(self):
        params = {
            "profundidad_defensiva": 0.9,
            "distancia_presion": 80,
            "ancho": 0.3,
            "altura_delanteros_defensiva": 0.8,
        }
        super().__init__("Catenaccio", params)

    def actualizar_defensa(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        es_local = equipo.es_local
        profundidad = self.params["profundidad_defensiva"]
        distancia_presion = self.params["distancia_presion"]

        poseedor = None
        if jugador_con_balon is not None and jugador_con_balon.equipo != equipo.nombre:
            poseedor = jugador_con_balon

        for i in range(1, 5):  # defensas (índices 1-4)
            jug = equipo.jugadores[i]
            if jug.es_controlado or hasattr(jug, 'expulsado') or hasattr(jug, 'lesionado'):
                continue

            velocidad_base = self._velocidad_efectiva(jug, factor=0.5)
            bx, by = self._posicion_base(i, es_local)

            porteria_x = 50 if es_local else SCREEN_WIDTH - 50
            if es_local:
                bx = porteria_x + (bx - porteria_x) * (1 - profundidad * 0.8)
            else:
                bx = porteria_x - (porteria_x - bx) * (1 - profundidad * 0.8)

            # Cerrar hacia el centro para reducir espacios
            centro_y = SCREEN_HEIGHT / 2
            by -= (by - centro_y) * 0.4

            if poseedor is not None:
                dist = distancia_objetos(jug, poseedor)
                if dist < distancia_presion * 1.5:
                    vx, vy = mover_hacia(jug, poseedor, velocidad_base * 1.0, dt)
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

            velocidad_base = self._velocidad_efectiva(jug, factor=0.6)
            bx, by = self._posicion_base(i, es_local)

            if poseedor is not None:
                dist = distancia_objetos(jug, poseedor)
                if dist < 150:
                    vx, vy = mover_hacia(jug, poseedor, velocidad_base * 0.9, dt)
                    jug.establecer_velocidad(vx, vy)
                    jug.actualizar(dt)
                    continue
                else:
                    if es_local:
                        bx = max(PLAYER_RADIUS, bx - 40)
                    else:
                        bx = min(SCREEN_WIDTH - PLAYER_RADIUS, bx + 40)

            destino = type('obj', (object,), {'x': bx, 'y': by})()
            if distancia_objetos(jug, destino) > 15:
                vx, vy = mover_hacia(jug, destino, velocidad_base * 0.5, dt)
                jug.establecer_velocidad(vx, vy)
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

            velocidad_base = self._velocidad_efectiva(jug, factor=0.7)
            porteria_x = SCREEN_WIDTH if es_local else 0
            porteria_y = SCREEN_HEIGHT // 2

            # --- Verificar si el poseedor está en nuestro campo ---
            en_nuestro_campo = False
            if poseedor is not None:
                if es_local and poseedor.x < SCREEN_WIDTH * 0.6:
                    en_nuestro_campo = True
                elif not es_local and poseedor.x > SCREEN_WIDTH * 0.4:
                    en_nuestro_campo = True

            if en_nuestro_campo:
                # Retroceder para ayudar en defensa
                retroceso_x = porteria_x + (SCREEN_WIDTH // 2 - porteria_x) * (1 - 0.8 * 0.7)
                destino = type('obj', (object,), {'x': retroceso_x, 'y': porteria_y + math.sin(jug.numero) * 50})()
                vx, vy = mover_hacia(jug, destino, velocidad_base * 0.6, dt)
                jug.establecer_velocidad(vx, vy)
                jug.actualizar(dt)
            else:
                # Mantenerse en zona ofensiva (esperando contraataque)
                angulo = math.sin(jug.numero * 1.5) * 1.2
                radio = 70 + (i - 9) * 20
                destino_x = porteria_x + math.cos(angulo) * radio
                destino_y = porteria_y + math.sin(angulo) * radio
                destino = type('obj', (object,), {'x': destino_x, 'y': destino_y})()
                vx, vy = mover_hacia(jug, destino, velocidad_base * 0.5, dt)
                jug.establecer_velocidad(vx, vy)
                jug.actualizar(dt)