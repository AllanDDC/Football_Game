# backend/tactics/base.py
"""
Clase base para todas las tácticas y funciones auxiliares compartidas.
"""

import math
from ..config import PLAYER_SPEED, SPRINT_MULTIPLIER, SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS
from ..physics import mover_hacia, distancia_objetos

# ------------------------------------------------------------
#  Formaciones (para usar en _posicion_base)
# ------------------------------------------------------------
FORMACION_LOCAL = [
    (0.10, 0.50),  # Portero (0)
    (0.25, 0.20),  # Defensa 1
    (0.25, 0.35),  # Defensa 2
    (0.25, 0.65),  # Defensa 3
    (0.25, 0.80),  # Defensa 4
    (0.45, 0.20),  # Mediocampista 1
    (0.45, 0.40),  # Mediocampista 2
    (0.45, 0.60),  # Mediocampista 3
    (0.45, 0.80),  # Mediocampista 4
    (0.70, 0.30),  # Delantero 1
    (0.70, 0.70),  # Delantero 2
]

FORMACION_RIVAL = [
    (0.90, 0.50),  # Portero
    (0.75, 0.20),  # Defensa 1
    (0.75, 0.35),  # Defensa 2
    (0.75, 0.65),  # Defensa 3
    (0.75, 0.80),  # Defensa 4
    (0.55, 0.20),  # Mediocampista 1
    (0.55, 0.40),  # Mediocampista 2
    (0.55, 0.60),  # Mediocampista 3
    (0.55, 0.80),  # Mediocampista 4
    (0.30, 0.30),  # Delantero 1
    (0.30, 0.70),  # Delantero 2
]

def _posicion_base(indice, es_local):
    """
    Retorna la posición base (x, y) en píxeles para un jugador dado su índice.
    """
    formacion = FORMACION_LOCAL if es_local else FORMACION_RIVAL
    if indice < len(formacion):
        fx, fy = formacion[indice]
        return (fx * SCREEN_WIDTH, fy * SCREEN_HEIGHT)
    return (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

def _get_velocidad_efectiva(jug, factor=0.5, sprint=False):
    """
    Calcula la velocidad efectiva del jugador considerando estadísticas, fatiga y sprint.
    """
    velocidad_base = PLAYER_SPEED * factor
    if hasattr(jug, 'stats'):
        stat_vel = jug.stats.velocidad / 100.0
        velocidad_base = PLAYER_SPEED * (factor * 0.4 + stat_vel * factor * 0.6)
        if sprint:
            velocidad_base *= SPRINT_MULTIPLIER
        if jug.stats.fatiga > 30:
            factor_fatiga = 1.0 - (jug.stats.fatiga - 30) / 100.0 * 0.5
            velocidad_base *= max(0.4, factor_fatiga)
    return velocidad_base


# ------------------------------------------------------------
#  Clase base de táctica (con métodos de conveniencia)
# ------------------------------------------------------------
class TacticaBase:
    def __init__(self, nombre, params):
        self.nombre = nombre
        self.params = params

    def obtener_param(self, key, default=None):
        return self.params.get(key, default)

    # Métodos de conveniencia que delegan en las funciones globales
    def _posicion_base(self, indice, es_local):
        return _posicion_base(indice, es_local)

    def _velocidad_efectiva(self, jug, factor=0.5, sprint=False):
        return _get_velocidad_efectiva(jug, factor, sprint)

    # Métodos que deben ser implementados por las subclases
    def actualizar_defensa(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        raise NotImplementedError

    def actualizar_mediocampistas(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        raise NotImplementedError

    def actualizar_delanteros(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        raise NotImplementedError