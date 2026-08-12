# backend/tactics/tiki_taka.py
from .base import TacticaBase
from ..physics import mover_hacia, distancia_objetos
from ..config import PLAYER_SPEED, SCREEN_WIDTH, SCREEN_HEIGHT


class TikiTaka(TacticaBase):
    """Táctica de posesión: presión alta tras pérdida, defensa adelantada."""

    def __init__(self):
        params = {
            "profundidad_defensiva": 0.3,
            "distancia_presion": 150,
            "ancho": 0.6,
            "altura_delanteros_defensiva": 0.2,
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

            velocidad_base = self._velocidad_efectiva(jug, factor=0.5)
            bx, by = self._posicion_base(i, es_local)

            # Defensa adelantada (poca profundidad)
            porteria_x = 50 if es_local else SCREEN_WIDTH - 50
            if es_local:
                bx = porteria_x + (bx - porteria_x) * (1 - profundidad * 0.5)
            else:
                bx = porteria_x - (porteria_x - bx) * (1 - profundidad * 0.5)

            if poseedor is not None:
                dist = distancia_objetos(jug, poseedor)
                if dist < distancia_presion:
                    # Presión alta: varios defensas pueden presionar
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

    # ... (similar para mediocampistas y delanteros, con presión alta)