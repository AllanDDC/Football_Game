# backend/tactics/jogo_bonito.py
"""
Táctica Jogo Bonito (estilo brasileño).
Características:
- Ataque creativo y fluido, con muchos regates y pases de fantasía.
- Jugadores con libertad para improvisar y buscar el 1vs1.
- Defensa basada en la posesión y recuperación hábil (robo).
- Laterales suben al ataque.
- Delanteros y mediocampistas se mueven constantemente para crear espacios.
- El portero participa en la construcción (sale del área).
- No es una táctica rígida, prioriza el espectáculo y la creatividad.
"""

import math
import random
from .base import TacticaBase
from ..physics import mover_hacia, distancia_objetos
from ..config import PLAYER_SPEED, SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS
from ..ai import _posicion_base, _get_velocidad_efectiva


class JogoBonito(TacticaBase):
    """
    Implementación de Jogo Bonito: creatividad, regate y fluidez.
    """

    def __init__(self):
        params = {
            "profundidad_defensiva": 0.4,       # línea media-alta
            "distancia_presion": 150,           # presión moderada
            "ancho": 0.8,                       # equipo abierto
            "altura_delanteros_defensiva": 0.3, # delanteros bajan un poco
            "presion_alta": 0.5,                # presión media
            "velocidad_ataque": 0.8,            # transiciones rápidas
            "regate_frecuencia": 0.9,           # máxima tendencia a regatear
            "pase_largo": 0.3,                  # pases cortos y combinativos
        }
        super().__init__("Jogo Bonito", params)

    # ------------------------------------------------------------
    #  Defensas: participan en ataque, laterales suben
    # ------------------------------------------------------------
    def actualizar_defensa(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        es_local = equipo.es_local
        profundidad = self.params["profundidad_defensiva"]
        distancia_presion = self.params["distancia_presion"]

        tiene_posesion = (jugador_con_balon is not None and 
                          jugador_con_balon.equipo == equipo.nombre)

        poseedor_rival = None
        if jugador_con_balon is not None and jugador_con_balon.equipo != equipo.nombre:
            poseedor_rival = jugador_con_balon

        for i in range(1, 5):  # defensas (índices 1-4)
            jug = equipo.jugadores[i]
            if jug.es_controlado or hasattr(jug, 'expulsado') or hasattr(jug, 'lesionado'):
                continue

            # Velocidad base
            velocidad_base = _get_velocidad_efectiva(jug, factor=0.5, sprint=False)

            # Posición base
            bx, by = _posicion_base(i, es_local)

            # Determinar si es lateral (índices pares o impares? En formación 4-4-2, los defensas laterales suelen ser los índices 2 y 3, pero depende)
            # Simplificamos: los defensas con índice par (2,4) serán laterales, los impares (1,3) centrales.
            es_lateral = (i % 2 == 0)

            if tiene_posesion:
                # ---- FASE OFENSIVA: laterales suben, centrales se quedan ----
                if es_lateral:
                    # Subir hasta la línea de mediocampo o más
                    if es_local:
                        bx = min(SCREEN_WIDTH * 0.7, bx + 120)
                    else:
                        bx = max(SCREEN_WIDTH * 0.3, bx - 120)
                    # Desmarcarse para dar opción de pase
                    if jugador_con_balon is not None:
                        angulo = math.atan2(jug.y - jugador_con_balon.y, jug.x - jugador_con_balon.x)
                        angulo += random.uniform(-0.3, 0.3)
                        radio = 100 + random.uniform(0, 50)
                        bx = jugador_con_balon.x + math.cos(angulo) * radio
                        by = jugador_con_balon.y + math.sin(angulo) * radio
                else:
                    # Centrales se mantienen en posición, pero pueden subir un poco
                    if es_local:
                        bx = min(SCREEN_WIDTH * 0.6, bx + 40)
                    else:
                        bx = max(SCREEN_WIDTH * 0.4, bx - 40)

            elif poseedor_rival is not None:
                # ---- FASE DEFENSIVA: presionar con habilidad (robo) ----
                dist = distancia_objetos(jug, poseedor_rival)
                # Presionar si el poseedor está en nuestro campo y no muy lejos
                if (es_local and poseedor_rival.x < SCREEN_WIDTH * 0.6) or (not es_local and poseedor_rival.x > SCREEN_WIDTH * 0.4):
                    if dist < distancia_presion:
                        # Intentar robar con más probabilidad (se maneja en el contacto)
                        velocidad = _get_velocidad_efectiva(jug, factor=0.5, sprint=False)
                        vx, vy = mover_hacia(jug, poseedor_rival, velocidad * 1.0, dt)
                        jug.establecer_velocidad(vx, vy)
                        jug.actualizar(dt)
                        continue
                # Si no presiona, retroceder a posición defensiva
                porteria_x = 50 if es_local else SCREEN_WIDTH - 50
                if es_local:
                    bx = porteria_x + (bx - porteria_x) * (1 - profundidad * 0.6)
                else:
                    bx = porteria_x - (porteria_x - bx) * (1 - profundidad * 0.6)

            # Moverse a la posición calculada
            destino = type('obj', (object,), {'x': bx, 'y': by})()
            if distancia_objetos(jug, destino) > 10:
                vx, vy = mover_hacia(jug, destino, velocidad_base * 0.7, dt)
                jug.establecer_velocidad(vx, vy)
                jug.actualizar(dt)
            else:
                jug.establecer_velocidad(0, 0)
                jug.actualizar(dt)

    # ------------------------------------------------------------
    #  Mediocampistas: creatividad, regates y pases de fantasía
    # ------------------------------------------------------------
    def actualizar_mediocampistas(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        es_local = equipo.es_local
        distancia_presion = self.params["distancia_presion"]

        tiene_posesion = (jugador_con_balon is not None and 
                          jugador_con_balon.equipo == equipo.nombre)

        poseedor_rival = None
        if jugador_con_balon is not None and jugador_con_balon.equipo != equipo.nombre:
            poseedor_rival = jugador_con_balon

        for i in range(5, 9):  # mediocampistas (índices 5-8)
            jug = equipo.jugadores[i]
            if jug.es_controlado or hasattr(jug, 'expulsado') or hasattr(jug, 'lesionado'):
                continue

            # Velocidad media-alta
            velocidad_base = _get_velocidad_efectiva(jug, factor=0.7, sprint=False)

            if tiene_posesion:
                # ---- FASE OFENSIVA: creatividad y desmarque ----
                if jug.tiene_balon:
                    # Si tiene el balón, intentar regatear (alta probabilidad)
                    # Esto se maneja en el contacto, pero aquí damos libertad de movimiento
                    # Avanzar con dribbling (movimiento impredecible)
                    porteria_x = SCREEN_WIDTH if es_local else 0
                    porteria_y = SCREEN_HEIGHT // 2
                    # Moverse hacia portería pero con zigzag
                    angulo = math.atan2(porteria_y - jug.y, porteria_x - jug.x)
                    angulo += random.uniform(-0.5, 0.5)  # desvío para simular regate
                    radio = 80
                    destino_x = jug.x + math.cos(angulo) * radio
                    destino_y = jug.y + math.sin(angulo) * radio
                    destino = type('obj', (object,), {'x': destino_x, 'y': destino_y})()
                    vx, vy = mover_hacia(jug, destino, velocidad_base * 1.0, dt)
                    jug.establecer_velocidad(vx, vy)
                    jug.actualizar(dt)
                    # Probabilidad de intentar un pase de fantasía (pase con efecto, etc.) - solo efecto visual
                    if random.random() < 0.02:
                        # Buscar un pase a un compañero cercano
                        from ..ball_control import ejecutar_pase
                        for comp in equipo.jugadores:
                            if comp != jug and distancia_objetos(jug, comp) < 200:
                                ejecutar_pase(jug, comp, pelota, es_largo=False)
                                break
                    continue

                # Sin balón: desmarcarse con movimientos impredecibles
                if jugador_con_balon is not None:
                    dist = distancia_objetos(jug, jugador_con_balon)
                    if dist > 60 and dist < 300:
                        # Moverse en ángulo aleatorio para crear espacios
                        angulo = math.atan2(jug.y - jugador_con_balon.y, jug.x - jugador_con_balon.x)
                        angulo += random.uniform(-1.0, 1.0)  # más aleatorio
                        radio = 100 + random.uniform(0, 80)
                        destino_x = jugador_con_balon.x + math.cos(angulo) * radio
                        destino_y = jugador_con_balon.y + math.sin(angulo) * radio
                        bx, by = destino_x, destino_y
                    else:
                        # Volver a posición base
                        bx, by = _posicion_base(i, es_local)
                else:
                    bx, by = _posicion_base(i, es_local)

            elif poseedor_rival is not None:
                # ---- FASE DEFENSIVA: presión selectiva y robo ----
                dist = distancia_objetos(jug, poseedor_rival)
                if dist < distancia_presion:
                    # Intentar robar (se maneja en contacto)
                    vx, vy = mover_hacia(jug, poseedor_rival, velocidad_base * 0.9, dt)
                    jug.establecer_velocidad(vx, vy)
                    jug.actualizar(dt)
                    continue
                else:
                    # Retroceder para cubrir espacios
                    bx, by = _posicion_base(i, es_local)
                    if es_local:
                        bx = max(PLAYER_RADIUS, bx - 30)
                    else:
                        bx = min(SCREEN_WIDTH - PLAYER_RADIUS, bx + 30)
            else:
                bx, by = _posicion_base(i, es_local)

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
    #  Delanteros: libertad total, buscan el gol con creatividad
    # ------------------------------------------------------------
    def actualizar_delanteros(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        es_local = equipo.es_local
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

            # Velocidad alta
            velocidad_base = _get_velocidad_efectiva(jug, factor=0.8, sprint=False)

            porteria_x = SCREEN_WIDTH if es_local else 0
            porteria_y = SCREEN_HEIGHT // 2

            if tiene_posesion:
                # ---- FASE OFENSIVA: buscar el gol con libertad ----
                if jug.tiene_balon:
                    # Intentar regatear hacia portería
                    destino = type('obj', (object,), {'x': porteria_x, 'y': porteria_y})()
                    vx, vy = mover_hacia(jug, destino, velocidad_base * 1.1, dt)
                    jug.establecer_velocidad(vx, vy)
                    jug.actualizar(dt)
                    # Alta probabilidad de disparar si está cerca
                    if distancia_objetos(jug, destino) < 300 and random.random() < 0.05:
                        from ..ball_control import ejecutar_tiro
                        ejecutar_tiro(jug, pelota)
                    continue

                # Sin balón: moverse constantemente en el área con movimientos impredecibles
                # Simular movimientos de desmarque: cambios de dirección aleatorios
                angulo = random.uniform(-2.0, 2.0)
                radio = 60 + random.uniform(0, 100)
                destino_x = porteria_x + math.cos(angulo) * radio
                destino_y = porteria_y + math.sin(angulo) * radio
                destino_x = max(PLAYER_RADIUS, min(SCREEN_WIDTH - PLAYER_RADIUS, destino_x))
                destino_y = max(PLAYER_RADIUS, min(SCREEN_HEIGHT - PLAYER_RADIUS, destino_y))
                destino = type('obj', (object,), {'x': destino_x, 'y': destino_y})()
                if distancia_objetos(jug, destino) > 15:
                    vx, vy = mover_hacia(jug, destino, velocidad_base * 0.9, dt)
                    jug.establecer_velocidad(vx, vy)
                    jug.actualizar(dt)
                else:
                    jug.establecer_velocidad(0, 0)
                    jug.actualizar(dt)

            elif poseedor_rival is not None:
                # ---- FASE DEFENSIVA: presión moderada, más que nada para robar ----
                dist = distancia_objetos(jug, poseedor_rival)
                # Si el poseedor está en campo rival, presionar con intensidad
                if (es_local and poseedor_rival.x < SCREEN_WIDTH * 0.6) or (not es_local and poseedor_rival.x > SCREEN_WIDTH * 0.4):
                    if dist < 150:
                        vx, vy = mover_hacia(jug, poseedor_rival, velocidad_base * 0.8, dt)
                        jug.establecer_velocidad(vx, vy)
                        jug.actualizar(dt)
                        continue

                # Si no presiona, retroceder según altura_delanteros_def (pero no mucho)
                retroceso_x = porteria_x + (SCREEN_WIDTH // 2 - porteria_x) * (1 - altura_delanteros_def * 0.5)
                retroceso_y = porteria_y + math.sin(jug.numero * 1.5) * 50
                destino = type('obj', (object,), {'x': retroceso_x, 'y': retroceso_y})()
                if distancia_objetos(jug, destino) > 15:
                    vx, vy = mover_hacia(jug, destino, velocidad_base * 0.4, dt)
                    jug.establecer_velocidad(vx, vy)
                    jug.actualizar(dt)
                else:
                    jug.establecer_velocidad(0, 0)
                    jug.actualizar(dt)
            else:
                # Si no hay poseedor, moverse en zona ofensiva
                angulo = random.uniform(-1.5, 1.5)
                radio = 70 + random.uniform(0, 60)
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