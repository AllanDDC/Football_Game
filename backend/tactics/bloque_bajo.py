# backend/tactics/bloque_bajo.py
"""
Táctica de Bloque Bajo (Low Block).
Características:
- Equipo muy replegado cerca de su portería
- Línea defensiva extremadamente baja
- Sin presión intensa, solo cierran espacios
- Jugadores muy juntos, sin amplitud
- Delanteros también retroceden hasta media cancha
- Buscan el error rival y salir rápido si hay oportunidad
- Muy difícil de penetrar por el centro
"""

import math
import random
from .base import TacticaBase
from ..physics import mover_hacia, distancia_objetos
from ..config import PLAYER_SPEED, SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS
from .base import _posicion_base, _get_velocidad_efectiva


class BloqueBajo(TacticaBase):
    """
    Implementación de bloque bajo: defensa ultracompacta y sin presión.
    """

    def __init__(self):
        params = {
            "profundidad_defensiva": 1.0,      # línea muy baja
            "distancia_presion": 40,            # presión solo a muy corta distancia
            "ancho": 0.1,                       # equipo muy centrado
            "altura_delanteros_defensiva": 1.0, # delanteros bajan hasta el centro del campo
            "presion_alta": 0.0,                # sin presión en campo rival
            "velocidad_ataque": 0.2,            # transiciones lentas
        }
        super().__init__("Bloque bajo", params)

    # ------------------------------------------------------------
    #  Defensas: ultrarepliegue, sin presión, solo tapar espacios
    # ------------------------------------------------------------
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

            # Velocidad muy baja (priorizan posición)
            velocidad_base = _get_velocidad_efectiva(jug, factor=0.4, sprint=False)

            # Posición base
            bx, by = _posicion_base(i, es_local)

            # Repliegue máximo (casi encima de la portería)
            porteria_x = 50 if es_local else SCREEN_WIDTH - 50
            if es_local:
                bx = porteria_x + (bx - porteria_x) * (1 - profundidad * 0.95)
            else:
                bx = porteria_x - (porteria_x - bx) * (1 - profundidad * 0.95)

            # Cerrar mucho hacia el centro para formar un bloque compacto
            centro_y = SCREEN_HEIGHT / 2
            by -= (by - centro_y) * 0.6

            # Presión solo si el poseedor está a muy corta distancia (dentro del área)
            if poseedor is not None:
                dist = distancia_objetos(jug, poseedor)
                # Solo presionar si el poseedor está dentro del área o muy cerca
                if (es_local and poseedor.x < 150) or (not es_local and poseedor.x > SCREEN_WIDTH - 150):
                    if dist < distancia_presion * 1.5:
                        vx, vy = mover_hacia(jug, poseedor, velocidad_base * 0.9, dt)
                        jug.establecer_velocidad(vx, vy)
                        jug.actualizar(dt)
                        continue

            # Si no presiona, mantener la posición (muy estática)
            destino = type('obj', (object,), {'x': bx, 'y': by})()
            if distancia_objetos(jug, destino) > 10:
                vx, vy = mover_hacia(jug, destino, velocidad_base * 0.5, dt)
                jug.establecer_velocidad(vx, vy)
                jug.actualizar(dt)
            else:
                jug.establecer_velocidad(0, 0)
                jug.actualizar(dt)

    # ------------------------------------------------------------
    #  Mediocampistas: retroceso total y solo presión en el área
    # ------------------------------------------------------------
    def actualizar_mediocampistas(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        es_local = equipo.es_local
        distancia_presion = self.params["distancia_presion"]

        poseedor = None
        if jugador_con_balon is not None and jugador_con_balon.equipo != equipo.nombre:
            poseedor = jugador_con_balon

        for i in range(5, 9):  # mediocampistas (índices 5-8)
            jug = equipo.jugadores[i]
            if jug.es_controlado or hasattr(jug, 'expulsado') or hasattr(jug, 'lesionado'):
                continue

            # Velocidad baja
            velocidad_base = _get_velocidad_efectiva(jug, factor=0.5, sprint=False)

            # Posición base
            bx, by = _posicion_base(i, es_local)

            # Retroceder mucho, cerca del área
            porteria_x = 50 if es_local else SCREEN_WIDTH - 50
            if es_local:
                bx = porteria_x + (bx - porteria_x) * 0.3
            else:
                bx = porteria_x - (porteria_x - bx) * 0.3

            # Cerrar hacia el centro
            centro_y = SCREEN_HEIGHT / 2
            by -= (by - centro_y) * 0.4

            # Presionar solo si el poseedor está en el área o muy cerca
            if poseedor is not None:
                dist = distancia_objetos(jug, poseedor)
                if (es_local and poseedor.x < 200) or (not es_local and poseedor.x > SCREEN_WIDTH - 200):
                    if dist < distancia_presion * 2:
                        vx, vy = mover_hacia(jug, poseedor, velocidad_base * 0.8, dt)
                        jug.establecer_velocidad(vx, vy)
                        jug.actualizar(dt)
                        continue

            destino = type('obj', (object,), {'x': bx, 'y': by})()
            if distancia_objetos(jug, destino) > 15:
                vx, vy = mover_hacia(jug, destino, velocidad_base * 0.5, dt)
                jug.establecer_velocidad(vx, vy)
                jug.actualizar(dt)
            else:
                jug.establecer_velocidad(0, 0)
                jug.actualizar(dt)

    # ------------------------------------------------------------
    #  Delanteros: retroceden hasta media cancha, buscan errores
    # ------------------------------------------------------------
    def actualizar_delanteros(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        es_local = equipo.es_local
        altura_delanteros_def = self.params["altura_delanteros_defensiva"]

        poseedor = None
        if jugador_con_balon is not None and jugador_con_balon.equipo != equipo.nombre:
            poseedor = jugador_con_balon

        # Detectar si el equipo está en transición ofensiva (poco común)
        en_transicion = (jugador_con_balon is not None and 
                         jugador_con_balon.equipo == equipo.nombre and
                         jugador_con_balon.vx != 0 and
                         distancia_objetos(jugador_con_balon, equipo.jugadores[0]) > 300)

        for i in range(9, 11):  # delanteros (índices 9-10)
            jug = equipo.jugadores[i]
            if jug.es_controlado or hasattr(jug, 'expulsado') or hasattr(jug, 'lesionado'):
                continue

            # Velocidad media (para posibles contraataques)
            sprint = en_transicion and jug.stats.fatiga < 60
            velocidad_base = _get_velocidad_efectiva(jug, factor=0.7, sprint=sprint)

            porteria_x = SCREEN_WIDTH if es_local else 0
            porteria_y = SCREEN_HEIGHT // 2

            if en_transicion:
                # Contraataque: avanzar rápido hacia portería rival
                destino_x = porteria_x + math.cos(jug.numero * 0.8) * 60
                destino_y = porteria_y + math.sin(jug.numero * 0.8) * 60
                destino = type('obj', (object,), {'x': destino_x, 'y': destino_y})()
                vx, vy = mover_hacia(jug, destino, velocidad_base * 1.0, dt)
                jug.establecer_velocidad(vx, vy)
                jug.actualizar(dt)
                continue

            # En defensa: retroceder hasta media cancha (nunca más arriba)
            retroceso_x = porteria_x + (SCREEN_WIDTH // 2 - porteria_x) * (1 - altura_delanteros_def * 0.8)
            retroceso_y = porteria_y + math.sin(jug.numero * 1.5) * 40
            destino = type('obj', (object,), {'x': retroceso_x, 'y': retroceso_y})()
            if distancia_objetos(jug, destino) > 15:
                vx, vy = mover_hacia(jug, destino, velocidad_base * 0.4, dt)
                jug.establecer_velocidad(vx, vy)
                jug.actualizar(dt)
            else:
                jug.establecer_velocidad(0, 0)
                jug.actualizar(dt)