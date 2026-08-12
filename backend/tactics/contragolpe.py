# backend/tactics/contragolpe.py
"""
Táctica de contragolpe (Counter‑attack).
Características:
- Línea defensiva baja (repliegue profundo)
- Presión selectiva solo cerca del área propia
- Transiciones ofensivas muy rápidas (pases largos)
- Delanteros esperan en la mitad rival para recibir balones largos
- Mediocampistas se repliegan para ayudar en defensa
- Aprovecha espacios a la contra con velocidad
"""

import math
from .base import TacticaBase
from ..physics import mover_hacia, distancia_objetos
from ..config import PLAYER_SPEED, SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS
from .base import _posicion_base, _get_velocidad_efectiva


class Contragolpe(TacticaBase):
    """
    Implementación de contragolpe: defensa profunda y salidas rápidas.
    """

    def __init__(self):
        params = {
            "profundidad_defensiva": 0.8,      # línea muy baja
            "distancia_presion": 60,           # presión solo muy cerca
            "ancho": 0.2,                      # equipo muy centrado
            "altura_delanteros_defensiva": 0.3, # delanteros no bajan del todo
            "velocidad_ataque": 1.0,            # máxima velocidad al contraatacar
            "pase_largo": 1.0,                 # tendencia máxima a pases largos
        }
        super().__init__("Contragolpe", params)

    # ------------------------------------------------------------
    #  Defensas: repliegue profundo, presión solo en área propia
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

            # Velocidad base (más lenta, priorizan posición)
            velocidad_base = _get_velocidad_efectiva(jug, factor=0.5, sprint=False)

            # Posición base
            bx, by = _posicion_base(i, es_local)

            # Repliegue muy profundo (cerca de la portería)
            porteria_x = 50 if es_local else SCREEN_WIDTH - 50
            if es_local:
                bx = porteria_x + (bx - porteria_x) * (1 - profundidad * 0.9)
            else:
                bx = porteria_x - (porteria_x - bx) * (1 - profundidad * 0.9)

            # Cerrar hacia el centro para tapar pasillos
            centro_y = SCREEN_HEIGHT / 2
            by -= (by - centro_y) * 0.5

            # Presión solo si el poseedor está muy cerca (en área propia)
            if poseedor is not None:
                dist = distancia_objetos(jug, poseedor)
                # Solo presionamos si el poseedor está en nuestro campo
                if (es_local and poseedor.x < SCREEN_WIDTH * 0.5) or (not es_local and poseedor.x > SCREEN_WIDTH * 0.5):
                    if dist < distancia_presion * 1.5:
                        # El defensa más cercano sale a presionar
                        vx, vy = mover_hacia(jug, poseedor, velocidad_base * 1.0, dt)
                        jug.establecer_velocidad(vx, vy)
                        jug.actualizar(dt)
                        continue
                # Si el poseedor está lejos, mantener la línea

            # Moverse a posición defensiva
            destino = type('obj', (object,), {'x': bx, 'y': by})()
            if distancia_objetos(jug, destino) > 10:
                vx, vy = mover_hacia(jug, destino, velocidad_base * 0.7, dt)
                jug.establecer_velocidad(vx, vy)
                jug.actualizar(dt)
            else:
                jug.establecer_velocidad(0, 0)
                jug.actualizar(dt)

    # ------------------------------------------------------------
    #  Mediocampistas: repliegue y pases largos en transición
    # ------------------------------------------------------------
    def actualizar_mediocampistas(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        es_local = equipo.es_local
        distancia_presion = self.params["distancia_presion"]

        poseedor = None
        if jugador_con_balon is not None and jugador_con_balon.equipo != equipo.nombre:
            poseedor = jugador_con_balon

        # Verificar si el equipo está en transición ofensiva (tiene el balón y está avanzando)
        en_transicion = (jugador_con_balon is not None and 
                         jugador_con_balon.equipo == equipo.nombre and
                         jugador_con_balon.vx != 0)

        for i in range(5, 9):  # mediocampistas (índices 5-8)
            jug = equipo.jugadores[i]
            if jug.es_controlado or hasattr(jug, 'expulsado') or hasattr(jug, 'lesionado'):
                continue

            # Velocidad base (en transición usan sprint)
            sprint = en_transicion and jug.stats.fatiga < 60
            velocidad_base = _get_velocidad_efectiva(jug, factor=0.6, sprint=sprint)

            if poseedor is not None and poseedor.equipo != equipo.nombre:
                dist = distancia_objetos(jug, poseedor)
                # Presionar solo si el poseedor está en campo propio y cerca
                if (es_local and poseedor.x < SCREEN_WIDTH * 0.6) or (not es_local and poseedor.x > SCREEN_WIDTH * 0.4):
                    if dist < distancia_presion * 2:
                        vx, vy = mover_hacia(jug, poseedor, velocidad_base * 0.9, dt)
                        jug.establecer_velocidad(vx, vy)
                        jug.actualizar(dt)
                        continue

            # Si estamos en transición ofensiva, avanzar rápido para apoyar el contraataque
            if en_transicion:
                # Avanzar hacia la portería rival
                porteria_x = SCREEN_WIDTH if es_local else 0
                porteria_y = SCREEN_HEIGHT // 2
                # Posición de ataque: más adelante que la base
                angulo = math.atan2(porteria_y - jug.y, porteria_x - jug.x)
                radio = 150
                destino_x = jug.x + math.cos(angulo) * radio
                destino_y = jug.y + math.sin(angulo) * radio
                destino_x = max(PLAYER_RADIUS, min(SCREEN_WIDTH - PLAYER_RADIUS, destino_x))
                destino_y = max(PLAYER_RADIUS, min(SCREEN_HEIGHT - PLAYER_RADIUS, destino_y))
                destino = type('obj', (object,), {'x': destino_x, 'y': destino_y})()
                if distancia_objetos(jug, destino) > 15:
                    vx, vy = mover_hacia(jug, destino, velocidad_base * 0.9, dt)
                    jug.establecer_velocidad(vx, vy)
                    jug.actualizar(dt)
                    continue

            # Si no, ocupar posición base (más retrasada para cubrir)
            bx, by = _posicion_base(i, es_local)
            # Retroceder más para ayudar en defensa
            if es_local:
                bx = max(PLAYER_RADIUS, bx - 30)
            else:
                bx = min(SCREEN_WIDTH - PLAYER_RADIUS, bx + 30)

            destino = type('obj', (object,), {'x': bx, 'y': by})()
            if distancia_objetos(jug, destino) > 15:
                vx, vy = mover_hacia(jug, destino, velocidad_base * 0.5, dt)
                jug.establecer_velocidad(vx, vy)
                jug.actualizar(dt)
            else:
                jug.establecer_velocidad(0, 0)
                jug.actualizar(dt)

    # ------------------------------------------------------------
    #  Delanteros: esperan en mitad rival para recibir pases largos
    # ------------------------------------------------------------
    def actualizar_delanteros(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        es_local = equipo.es_local
        altura_delanteros_def = self.params["altura_delanteros_defensiva"]

        # Verificar si el equipo está en transición ofensiva
        en_transicion = (jugador_con_balon is not None and 
                         jugador_con_balon.equipo == equipo.nombre and
                         jugador_con_balon.vx != 0)

        for i in range(9, 11):  # delanteros (índices 9-10)
            jug = equipo.jugadores[i]
            if jug.es_controlado or hasattr(jug, 'expulsado') or hasattr(jug, 'lesionado'):
                continue

            # Velocidad alta (más rápidos para el contraataque)
            sprint = en_transicion and jug.stats.fatiga < 60
            velocidad_base = _get_velocidad_efectiva(jug, factor=0.8, sprint=sprint)

            porteria_x = SCREEN_WIDTH if es_local else 0
            porteria_y = SCREEN_HEIGHT // 2

            # En transición ofensiva: correr hacia la portería rival (buscar el pase largo)
            if en_transicion:
                # Buscar espacio entre defensas rivales
                destino_x = porteria_x + math.cos(jug.numero * 0.8) * 60
                destino_y = porteria_y + math.sin(jug.numero * 0.8) * 60
                destino = type('obj', (object,), {'x': destino_x, 'y': destino_y})()
                vx, vy = mover_hacia(jug, destino, velocidad_base * 1.1, dt)
                jug.establecer_velocidad(vx, vy)
                jug.actualizar(dt)
                continue

            # En defensa: esperar en la mitad rival (no bajan del todo)
            # Retroceder ligeramente según altura_delanteros_def
            retroceso_x = porteria_x + (SCREEN_WIDTH // 2 - porteria_x) * (1 - altura_delanteros_def * 0.6)
            retroceso_y = porteria_y + math.sin(jug.numero * 1.5) * 50
            destino = type('obj', (object,), {'x': retroceso_x, 'y': retroceso_y})()
            if distancia_objetos(jug, destino) > 15:
                vx, vy = mover_hacia(jug, destino, velocidad_base * 0.5, dt)
                jug.establecer_velocidad(vx, vy)
                jug.actualizar(dt)
            else:
                jug.establecer_velocidad(0, 0)
                jug.actualizar(dt)