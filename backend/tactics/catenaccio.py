# backend/tactics/catenaccio.py
import math
from .base import TacticaBase
from ..physics import mover_hacia, distancia_objetos
from ..config import PLAYER_SPEED, SCREEN_WIDTH, SCREEN_HEIGHT


class Catenaccio(TacticaBase):
    """
    Táctica ultradefensiva: repliegue en bloque, presión solo del más cercano,
    los demás cubren espacios y cierran pasillos.
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

        # Determinar poseedor (si es rival)
        poseedor = None
        if jugador_con_balon is not None and jugador_con_balon.equipo != equipo.nombre:
            poseedor = jugador_con_balon

        for i in range(1, 5):  # defensas (índices 1-4)
            jug = equipo.jugadores[i]
            if jug.es_controlado or hasattr(jug, 'expulsado') or hasattr(jug, 'lesionado'):
                continue

            # Velocidad base
            velocidad_base = self._velocidad_efectiva(jug, factor=0.5)

            # Posición base
            bx, by = self._posicion_base(i, es_local)

            # Posición defensiva: cerca de la portería
            porteria_x = 50 if es_local else SCREEN_WIDTH - 50
            if es_local:
                bx = porteria_x + (bx - porteria_x) * (1 - profundidad * 0.8)
            else:
                bx = porteria_x - (porteria_x - bx) * (1 - profundidad * 0.8)

            # Cerrar hacia el centro para reducir espacios
            centro_y = SCREEN_HEIGHT / 2
            by -= (by - centro_y) * 0.4

            # Si hay poseedor y está cerca, el defensa más cercano presiona
            if poseedor is not None:
                dist = distancia_objetos(jug, poseedor)
                if dist < distancia_presion * 1.5:
                    # Solo el más cercano presiona
                    vx, vy = mover_hacia(jug, poseedor, velocidad_base * 1.0, dt)
                    jug.establecer_velocidad(vx, vy)
                    jug.actualizar(dt)
                    continue

            # Moverse a posición defensiva
            destino = type('obj', (object,), {'x': bx, 'y': by})()
            if distancia_objetos(jug, destino) > 10:
                vx, vy = mover_hacia(jug, destino, velocidad_base * 0.7, dt)
                jug.establecer_velocidad(vx, vy)
                jug.actualizar(dt)
            else:
                jug.establecer_velocidad(0, 0)
                jug.actualizar(dt)

    def actualizar_mediocampistas(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        # Similar a defensa pero con más apoyo
        es_local = equipo.es_local
        poseedor = None
        if jugador_con_balon is not None and jugador_con_balon.equipo != equipo.nombre:
            poseedor = jugador_con_balon

        for i in range(5, 9):  # mediocampistas (índices 5-8)
            jug = equipo.jugadores[i]
            if jug.es_controlado or hasattr(jug, 'expulsado') or hasattr(jug, 'lesionado'):
                continue

            velocidad_base = self._velocidad_efectiva(jug, factor=0.6)
            bx, by = self._posicion_base(i, es_local)

            # En defensa, retroceder
            if poseedor is not None:
                dist = distancia_objetos(jug, poseedor)
                if dist < 150:
                    # Presionar al poseedor si está muy cerca
                    vx, vy = mover_hacia(jug, poseedor, velocidad_base * 0.9, dt)
                    jug.establecer_velocidad(vx, vy)
                    jug.actualizar(dt)
                    continue
                else:
                    # Retroceder hacia el centro
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

        for i in range(9, 11):  # delanteros
            jug = equipo.jugadores[i]
            if jug.es_controlado or hasattr(jug, 'expulsado') or hasattr(jug, 'lesionado'):
                continue

            velocidad_base = self._velocidad_efectiva(jug, factor=0.7)
            porteria_x = SCREEN_WIDTH if es_local else 0
            porteria_y = SCREEN_HEIGHT // 2

            # En defensa, los delanteros retroceden hasta medio campo
            if poseedor is not None and (es_local and poseedor.x < SCREEN_WIDTH * 0.6) or (not es_local and poseedor.x > SCREEN_WIDTH * 0.4):
                # Retroceder
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