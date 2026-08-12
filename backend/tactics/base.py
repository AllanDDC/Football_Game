# backend/tactics/base.py
import math
from ..physics import mover_hacia, distancia_objetos
from ..config import PLAYER_SPEED, SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS


class TacticaBase:
    """
    Clase base para todas las tácticas.
    Define métodos que cada táctica debe implementar.
    """

    def __init__(self, nombre, params):
        self.nombre = nombre
        self.params = params

    def obtener_param(self, key, default=None):
        return self.params.get(key, default)

    # ---------- Comportamiento defensivo ----------
    def actualizar_defensa(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        """
        Actualiza el movimiento de los jugadores defensivos (índices 1-4).
        Cada táctica implementa su propia lógica de repliegue y presión.
        """
        raise NotImplementedError

    # ---------- Comportamiento de mediocampistas ----------
    def actualizar_mediocampistas(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        raise NotImplementedError

    # ---------- Comportamiento de delanteros ----------
    def actualizar_delanteros(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        raise NotImplementedError

    # ---------- Utilidades auxiliares ----------
    def _velocidad_efectiva(self, jug, factor=0.5, sprint=False):
        """Calcula velocidad efectiva con estadísticas y fatiga."""
        from ..ai import _get_velocidad_efectiva
        return _get_velocidad_efectiva(jug, factor, sprint)

    def _posicion_base(self, indice, es_local):
        """Obtiene la posición base según formación."""
        from ..ai import _posicion_base, FORMACION_LOCAL, FORMACION_RIVAL
        formacion = FORMACION_LOCAL if es_local else FORMACION_RIVAL
        return _posicion_base(indice, formacion)