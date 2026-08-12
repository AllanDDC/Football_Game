# backend/tactics/presion_alta.py
"""
Táctica de presión alta (Gegenpressing).
Características:
- Línea defensiva muy alta (poca profundidad)
- Presión intensa al portador del balón en cualquier zona del campo
- Recuperación rápida tras pérdida
- Defensas y mediocampistas presionan agresivamente
- Delanteros presionan desde el inicio (sobre el portero rival)
"""

import math
from .base import TacticaBase
from ..physics import mover_hacia, distancia_objetos
from ..config import PLAYER_SPEED, SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS
from ..ai import _posicion_base, _get_velocidad_efectiva


class PresionAlta(TacticaBase):
    """
    Implementación de presión alta: recuperación inmediata del balón en campo rival.
    """

    def __init__(self):
        params = {
            "profundidad_defensiva": 0.1,     # línea muy alta
            "distancia_presion": 250,         # gran radio de presión
            "ancho": 0.5,
            "altura_delanteros_defensiva": 0.1, # delanteros siempre arriba
            "presion_alta": 1.0,               # intensidad máxima
        }
        super().__init__("Presión alta", params)

    # ------------------------------------------------------------
    #  Defensas: línea alta, presión en campo rival
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

            # Velocidad efectiva (ligeramente mayor para presionar)
            velocidad_base = _get_velocidad_efectiva(jug, factor=0.6, sprint=False)

            # Posición base (muy adelantada)
            bx, by = _posicion_base(i, es_local)

            # Línea defensiva alta: apenas retrocedemos
            porteria_x = 50 if es_local else SCREEN_WIDTH - 50
            if es_local:
                bx = porteria_x + (bx - porteria_x) * (1 - profundidad * 0.3)
            else:
                bx = porteria_x - (porteria_x - bx) * (1 - profundidad * 0.3)

            # Si hay poseedor, presión agresiva
            if poseedor is not None:
                dist = distancia_objetos(jug, poseedor)
                # Presionar incluso si está en campo rival (si estamos cerca)
                if dist < distancia_presion:
                    # Usar sprint para presionar rápido
                    velocidad = _get_velocidad_efectiva(jug, factor=0.6, sprint=True)
                    vx, vy = mover_hacia(jug, poseedor, velocidad * 1.2, dt)
                    jug.establecer_velocidad(vx, vy)
                    jug.actualizar(dt)
                    continue

            # Moverse a posición defensiva (pero alta)
            destino = type('obj', (object,), {'x': bx, 'y': by})()
            if distancia_objetos(jug, destino) > 10:
                vx, vy = mover_hacia(jug, destino, velocidad_base * 0.7, dt)
                jug.establecer_velocidad(vx, vy)
                jug.actualizar(dt)
            else:
                jug.establecer_velocidad(0, 0)
                jug.actualizar(dt)

    # ------------------------------------------------------------
    #  Mediocampistas: presión en todo el campo
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

            # Velocidad media
            velocidad_base = _get_velocidad_efectiva(jug, factor=0.7, sprint=False)

            if poseedor is not None:
                dist = distancia_objetos(jug, poseedor)
                # Presionar agresivamente si el poseedor está en campo rival o cerca
                if dist < distancia_presion:
                    velocidad = _get_velocidad_efectiva(jug, factor=0.7, sprint=True)
                    vx, vy = mover_hacia(jug, poseedor, velocidad * 1.1, dt)
                    jug.establecer_velocidad(vx, vy)
                    jug.actualizar(dt)
                    continue

            # Si no presiona, ocupar posición base (pero adelantada)
            bx, by = _posicion_base(i, es_local)
            # Adelantar ligeramente la posición
            if es_local:
                bx += 30
            else:
                bx -= 30

            destino = type('obj', (object,), {'x': bx, 'y': by})()
            if distancia_objetos(jug, destino) > 15:
                vx, vy = mover_hacia(jug, destino, velocidad_base * 0.6, dt)
                jug.establecer_velocidad(vx, vy)
                jug.actualizar(dt)
            else:
                jug.establecer_velocidad(0, 0)
                jug.actualizar(dt)

    # ------------------------------------------------------------
    #  Delanteros: presión desde el primer momento (sobre el portero)
    # ------------------------------------------------------------
    def actualizar_delanteros(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        es_local = equipo.es_local
        distancia_presion = self.params["distancia_presion"]

        poseedor = None
        if jugador_con_balon is not None and jugador_con_balon.equipo != equipo.nombre:
            poseedor = jugador_con_balon

        for i in range(9, 11):  # delanteros (índices 9-10)
            jug = equipo.jugadores[i]
            if jug.es_controlado or hasattr(jug, 'expulsado') or hasattr(jug, 'lesionado'):
                continue

            # Velocidad alta (más rápidos para presionar)
            velocidad_base = _get_velocidad_efectiva(jug, factor=0.8, sprint=False)

            # Si hay poseedor, presionar siempre que esté en campo rival o cerca
            if poseedor is not None:
                dist = distancia_objetos(jug, poseedor)
                # Presionar al portero o defensas rivales
                if dist < distancia_presion or (es_local and poseedor.x < SCREEN_WIDTH * 0.6) or (not es_local and poseedor.x > SCREEN_WIDTH * 0.4):
                    velocidad = _get_velocidad_efectiva(jug, factor=0.8, sprint=True)
                    vx, vy = mover_hacia(jug, poseedor, velocidad * 1.0, dt)
                    jug.establecer_velocidad(vx, vy)
                    jug.actualizar(dt)
                    continue

            # Si no presiona, mantenerse en zona ofensiva (cerca de portería rival)
            porteria_x = SCREEN_WIDTH if es_local else 0
            porteria_y = SCREEN_HEIGHT // 2
            angulo = math.sin(jug.numero * 1.5) * 1.2
            radio = 60 + (i - 9) * 20
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