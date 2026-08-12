# backend/tactics/total.py
"""
Táctica de Fútbol Total (Total Football).
Características:
- Movilidad constante: todos los jugadores atacan y defienden
- Rotación de posiciones: jugadores intercambian roles dinámicamente
- Línea defensiva alta (presión en campo rival)
- Defensas se incorporan al ataque
- Delanteros presionan alto y también retroceden
- Mediocampistas cubren espacios y apoyan en ambas fases
- Estilo muy dinámico y fluido
"""

import math
import random
from .base import TacticaBase
from ..physics import mover_hacia, distancia_objetos
from ..config import PLAYER_SPEED, SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS
from .base import _posicion_base, _get_velocidad_efectiva


class Total(TacticaBase):
    """
    Implementación de Fútbol Total: fluidez, rotación y presión constante.
    """

    def __init__(self):
        params = {
            "profundidad_defensiva": 0.4,       # línea media-alta
            "distancia_presion": 200,           # presión en campo rival
            "ancho": 0.8,                       # equipo muy abierto
            "altura_delanteros_defensiva": 0.4, # delanteros bajan a media cancha
            "presion_alta": 0.8,                # presión intensa
            "velocidad_ataque": 0.8,            # transiciones rápidas
            "regate_frecuencia": 0.7,           # mucho regate
        }
        super().__init__("Fútbol total", params)

    # ------------------------------------------------------------
    #  Defensas: se incorporan al ataque, presionan alto
    # ------------------------------------------------------------
    def actualizar_defensa(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        es_local = equipo.es_local
        profundidad = self.params["profundidad_defensiva"]
        distancia_presion = self.params["distancia_presion"]

        # Detectar si el equipo tiene el balón
        tiene_posesion = (jugador_con_balon is not None and 
                          jugador_con_balon.equipo == equipo.nombre)

        poseedor_rival = None
        if jugador_con_balon is not None and jugador_con_balon.equipo != equipo.nombre:
            poseedor_rival = jugador_con_balon

        for i in range(1, 5):  # defensas (índices 1-4)
            jug = equipo.jugadores[i]
            if jug.es_controlado or hasattr(jug, 'expulsado') or hasattr(jug, 'lesionado'):
                continue

            # Velocidad base (mayor para apoyar ataque)
            velocidad_base = _get_velocidad_efectiva(jug, factor=0.6, sprint=False)

            # Posición base
            bx, by = _posicion_base(i, es_local)

            if tiene_posesion:
                # ---- FASE OFENSIVA: defensas suben para apoyar ----
                # Subir hasta la mitad del campo o más
                if es_local:
                    bx = bx + 100  # se adelantan
                else:
                    bx = bx - 100
                # Si hay balón y estamos cerca, apoyar como mediocampista
                if jugador_con_balon is not None:
                    dist = distancia_objetos(jug, jugador_con_balon)
                    if dist > 100 and dist < 300:
                        # Desmarcarse en ángulo para dar opción de pase
                        angulo = math.atan2(jug.y - jugador_con_balon.y, jug.x - jugador_con_balon.x)
                        angulo += random.uniform(-0.5, 0.5)
                        radio = 150
                        destino_x = jugador_con_balon.x + math.cos(angulo) * radio
                        destino_y = jugador_con_balon.y + math.sin(angulo) * radio
                        bx, by = destino_x, destino_y

                # Limitar dentro del campo
                bx = max(PLAYER_RADIUS, min(SCREEN_WIDTH - PLAYER_RADIUS, bx))
                by = max(PLAYER_RADIUS, min(SCREEN_HEIGHT - PLAYER_RADIUS, by))

            elif poseedor_rival is not None:
                # ---- FASE DEFENSIVA: presionar alto si es posible ----
                dist = distancia_objetos(jug, poseedor_rival)
                # Si el poseedor está en campo rival (o cerca de la mitad), presionar
                if (es_local and poseedor_rival.x < SCREEN_WIDTH * 0.7) or (not es_local and poseedor_rival.x > SCREEN_WIDTH * 0.3):
                    if dist < distancia_presion:
                        # Usar sprint para presionar rápido
                        velocidad = _get_velocidad_efectiva(jug, factor=0.6, sprint=True)
                        vx, vy = mover_hacia(jug, poseedor_rival, velocidad * 1.2, dt)
                        jug.establecer_velocidad(vx, vy)
                        jug.actualizar(dt)
                        continue
                # Si no presiona, retroceder a posición defensiva (pero no tan profundo)
                porteria_x = 50 if es_local else SCREEN_WIDTH - 50
                if es_local:
                    bx = porteria_x + (bx - porteria_x) * (1 - profundidad * 0.6)
                else:
                    bx = porteria_x - (porteria_x - bx) * (1 - profundidad * 0.6)

            # Moverse a la posición calculada
            destino = type('obj', (object,), {'x': bx, 'y': by})()
            if distancia_objetos(jug, destino) > 10:
                vx, vy = mover_hacia(jug, destino, velocidad_base * 0.8, dt)
                jug.establecer_velocidad(vx, vy)
                jug.actualizar(dt)
            else:
                jug.establecer_velocidad(0, 0)
                jug.actualizar(dt)

    # ------------------------------------------------------------
    #  Mediocampistas: rotación, apoyo y presión constante
    # ------------------------------------------------------------
    def actualizar_mediocampistas(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        es_local = equipo.es_local
        distancia_presion = self.params["distancia_presion"]

        tiene_posesion = (jugador_con_balon is not None and 
                          jugador_con_balon.equipo == equipo.nombre)

        poseedor_rival = None
        if jugador_con_balon is not None and jugador_con_balon.equipo != equipo.nombre:
            poseedor_rival = jugador_con_balon

        # Factor de rotación (varía ligeramente cada cierto tiempo)
        rotacion = math.sin(jugador_con_balon.x * 0.01 if jugador_con_balon else 0) * 0.5

        for i in range(5, 9):  # mediocampistas (índices 5-8)
            jug = equipo.jugadores[i]
            if jug.es_controlado or hasattr(jug, 'expulsado') or hasattr(jug, 'lesionado'):
                continue

            # Velocidad media-alta (muy móviles)
            velocidad_base = _get_velocidad_efectiva(jug, factor=0.7, sprint=False)

            # Posición base con rotación
            bx, by = _posicion_base(i, es_local)
            # Rotación: intercambiar posiciones entre mediocampistas
            if random.random() < 0.02:  # rotación aleatoria
                # Intercambiar con otro mediocampista del mismo equipo
                otros = [j for j in range(5, 9) if j != i]
                if otros:
                    otro_idx = random.choice(otros)
                    otro = equipo.jugadores[otro_idx]
                    # Intercambiar posiciones base (simulación de rotación)
                    bx_temp, by_temp = _posicion_base(otro_idx, es_local)
                    bx, by = bx_temp, by_temp

            if tiene_posesion:
                # ---- FASE OFENSIVA: desmarque y apoyo ----
                if jug.tiene_balon:
                    # Avanzar hacia portería rival
                    porteria_x = SCREEN_WIDTH if es_local else 0
                    porteria_y = SCREEN_HEIGHT // 2
                    destino = type('obj', (object,), {'x': porteria_x, 'y': porteria_y})()
                    vx, vy = mover_hacia(jug, destino, velocidad_base * 1.0, dt)
                    jug.establecer_velocidad(vx, vy)
                    jug.actualizar(dt)
                    # Intentar pase o tiro (probabilidad)
                    if random.random() < 0.03:
                        from ..ball_control import ejecutar_pase, ejecutar_tiro
                        # Si está cerca, tirar
                        if distancia_objetos(jug, destino) < 300:
                            ejecutar_tiro(jug, pelota)
                        else:
                            # Buscar pase a delantero
                            for comp in equipo.jugadores[9:11]:
                                if distancia_objetos(jug, comp) < 200:
                                    ejecutar_pase(jug, comp, pelota, es_largo=False)
                                    break
                    continue

                # Sin balón: desmarcarse para recibir
                if jugador_con_balon is not None:
                    dist = distancia_objetos(jug, jugador_con_balon)
                    if dist > 80 and dist < 300:
                        angulo = math.atan2(jug.y - jugador_con_balon.y, jug.x - jugador_con_balon.x)
                        angulo += random.uniform(-0.8, 0.8)
                        radio = 120 + random.uniform(0, 30)
                        destino_x = jugador_con_balon.x + math.cos(angulo) * radio
                        destino_y = jugador_con_balon.y + math.sin(angulo) * radio
                        bx, by = destino_x, destino_y

            elif poseedor_rival is not None:
                # ---- FASE DEFENSIVA: presión alta ----
                dist = distancia_objetos(jug, poseedor_rival)
                if dist < distancia_presion:
                    velocidad = _get_velocidad_efectiva(jug, factor=0.7, sprint=True)
                    vx, vy = mover_hacia(jug, poseedor_rival, velocidad * 1.1, dt)
                    jug.establecer_velocidad(vx, vy)
                    jug.actualizar(dt)
                    continue
                else:
                    # Retroceder para cubrir espacios
                    if es_local:
                        bx = max(PLAYER_RADIUS, bx - 30)
                    else:
                        bx = min(SCREEN_WIDTH - PLAYER_RADIUS, bx + 30)

            # Moverse a la posición calculada
            destino = type('obj', (object,), {'x': bx, 'y': by})()
            if distancia_objetos(jug, destino) > 15:
                vx, vy = mover_hacia(jug, destino, velocidad_base * 0.7, dt)
                jug.establecer_velocidad(vx, vy)
                jug.actualizar(dt)
            else:
                jug.establecer_velocidad(0, 0)
                jug.actualizar(dt)

    # ------------------------------------------------------------
    #  Delanteros: presión alta y repliegue moderado
    # ------------------------------------------------------------
    def actualizar_delanteros(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        es_local = equipo.es_local
        distancia_presion = self.params["distancia_presion"]
        altura_delanteros_def = self.params["altura_delanteros_defensiva"]

        tiene_posesion = (jugador_con_balon is not None and 
                          jugador_con_balon.equipo == equipo.nombre)

        poseedor_rival = None
        if jugador_con_balon is not None and jugador_con_balon.equipo != equipo.nombre:
            poseedor_rival = jugador_con_balon

        for i in range(9, 11):  # delanteros (índices 9-10)
            jug = equipo.jugadores[i]
            if jug.es_controlado or hasattr(jug, 'expulsado') or hasattr(jug, 'lesionado'):
                continue

            # Velocidad alta (para presión y ataque)
            velocidad_base = _get_velocidad_efectiva(jug, factor=0.8, sprint=False)

            porteria_x = SCREEN_WIDTH if es_local else 0
            porteria_y = SCREEN_HEIGHT // 2

            if tiene_posesion:
                # ---- FASE OFENSIVA: buscar portería ----
                if jug.tiene_balon:
                    destino = type('obj', (object,), {'x': porteria_x, 'y': porteria_y})()
                    vx, vy = mover_hacia(jug, destino, velocidad_base * 1.1, dt)
                    jug.establecer_velocidad(vx, vy)
                    jug.actualizar(dt)
                    if distancia_objetos(jug, destino) < 250 and random.random() < 0.03:
                        from ..ball_control import ejecutar_tiro
                        ejecutar_tiro(jug, pelota)
                    continue

                # Sin balón: desmarcarse en área rival
                angulo = random.uniform(-1.2, 1.2)
                radio = 80 + random.uniform(0, 50)
                destino_x = porteria_x + math.cos(angulo) * radio
                destino_y = porteria_y + math.sin(angulo) * radio
                destino = type('obj', (object,), {'x': destino_x, 'y': destino_y})()
                if distancia_objetos(jug, destino) > 15:
                    vx, vy = mover_hacia(jug, destino, velocidad_base * 0.9, dt)
                    jug.establecer_velocidad(vx, vy)
                    jug.actualizar(dt)
                else:
                    jug.establecer_velocidad(0, 0)
                    jug.actualizar(dt)

            elif poseedor_rival is not None:
                # ---- FASE DEFENSIVA: presión alta y repliegue ----
                dist = distancia_objetos(jug, poseedor_rival)
                # Si el poseedor está en campo rival o en la mitad, presionar
                if (es_local and poseedor_rival.x < SCREEN_WIDTH * 0.6) or (not es_local and poseedor_rival.x > SCREEN_WIDTH * 0.4):
                    if dist < distancia_presion:
                        velocidad = _get_velocidad_efectiva(jug, factor=0.8, sprint=True)
                        vx, vy = mover_hacia(jug, poseedor_rival, velocidad * 1.0, dt)
                        jug.establecer_velocidad(vx, vy)
                        jug.actualizar(dt)
                        continue

                # Si no presiona, retroceder según altura_delanteros_def
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