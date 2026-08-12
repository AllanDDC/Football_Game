# backend/tactics/base.py
"""
Clase base para todas las tácticas y funciones auxiliares compartidas.
Incluye método de movimiento con sprint automático.
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
    """Retorna la posición base (x, y) en píxeles para un jugador dado su índice."""
    formacion = FORMACION_LOCAL if es_local else FORMACION_RIVAL
    if indice < len(formacion):
        fx, fy = formacion[indice]
        return (fx * SCREEN_WIDTH, fy * SCREEN_HEIGHT)
    return (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

def _get_velocidad_efectiva(jug, factor=0.5, sprint=False):
    """Calcula la velocidad efectiva del jugador considerando estadísticas, fatiga y sprint."""
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
#  Decisión de sprint (función universal)
# ------------------------------------------------------------
def decidir_sprint(jug, poseedor, pelota, equipo, equipo_rival):
    """
    Decide si un jugador debe usar sprint en función del contexto.
    Retorna True si debería sprintar, False en caso contrario.
    """
    # Si está muy cansado, no sprintar
    if hasattr(jug, 'stats') and jug.stats.fatiga > 80:
        return False

    # Caso 1: Presión al poseedor (distancia < 150 y acorralado)
    if poseedor is not None and poseedor.equipo != equipo.nombre:
        dist = distancia_objetos(jug, poseedor)
        if dist < 150:
            # Si el poseedor está cerca de la banda o encerrado
            if poseedor.x < 60 or poseedor.x > SCREEN_WIDTH - 60 or poseedor.y < 60 or poseedor.y > SCREEN_HEIGHT - 60:
                return True
            # Si el poseedor tiene pocos compañeros cerca (acorralado)
            companeros_cerca = sum(1 for comp in equipo_rival.jugadores if distancia_objetos(poseedor, comp) < 80)
            if companeros_cerca < 2:
                return True
            # Si el jugador está muy cerca (< 80), sprint para robar
            if dist < 80:
                return True
            return False

    # Caso 2: Balón suelto (cerca y alcanzable)
    if pelota.dueno is None and not pelota.pegada:
        dist_balon = distancia_objetos(jug, pelota)
        if dist_balon < 100 and dist_balon > 20:
            return True

    # Caso 3: Contraataque (equipo recupera y hay espacio adelante)
    poseedor_propio = poseedor is not None and poseedor.equipo == equipo.nombre
    if poseedor_propio and not jug.tiene_balon:
        # Delanteros o extremos en posición de contraataque
        if jug.numero >= 9:  # delanteros
            porteria_x = SCREEN_WIDTH if equipo.es_local else 0
            if (equipo.es_local and jug.x < SCREEN_WIDTH * 0.7) or (not equipo.es_local and jug.x > SCREEN_WIDTH * 0.3):
                return True
        # Mediocampistas que se proyectan
        elif 5 <= jug.numero <= 8:
            if (equipo.es_local and jug.x < SCREEN_WIDTH * 0.6) or (not equipo.es_local and jug.x > SCREEN_WIDTH * 0.4):
                return True

    # Caso 4: Cierre de espacios en defensa (si hay un hueco)
    if poseedor is not None and poseedor.equipo != equipo.nombre:
        # Si es defensa y está muy lejos de la línea
        if jug.numero < 5:
            # Obtener posición base de la línea defensiva
            _, by = _posicion_base(jug.numero, equipo.es_local)
            if abs(jug.y - by) > 80:
                return True

    return False


# ------------------------------------------------------------
#  Clase base de táctica (con sprint integrado)
# ------------------------------------------------------------
class TacticaBase:
    def __init__(self, nombre, params):
        self.nombre = nombre
        self.params = params

    def obtener_param(self, key, default=None):
        return self.params.get(key, default)

    def _posicion_base(self, indice, es_local):
        return _posicion_base(indice, es_local)

    def _velocidad_efectiva(self, jug, factor=0.5, sprint=False):
        return _get_velocidad_efectiva(jug, factor, sprint)

    def _mover_jugador(self, jug, destino_x, destino_y, dt,
                       poseedor, pelota, equipo, equipo_rival,
                       factor=0.7, fuerza_extra=1.0):
        """
        Mueve al jugador hacia el destino decidiendo automáticamente si sprintar.
        """
        # 1. Decidir si sprintar
        sprint = decidir_sprint(jug, poseedor, pelota, equipo, equipo_rival)

        # 2. Calcular velocidad efectiva
        velocidad = self._velocidad_efectiva(jug, factor=factor, sprint=sprint)
        velocidad *= fuerza_extra

        # 3. Crear objeto destino
        destino = type('obj', (object,), {'x': destino_x, 'y': destino_y})

        # 4. Si ya está muy cerca, detener
        if distancia_objetos(jug, destino) < 5:
            jug.establecer_velocidad(0, 0)
            jug.actualizar(dt)
            return

        # 5. Mover hacia el destino
        vx, vy = mover_hacia(jug, destino, velocidad, dt)
        jug.establecer_velocidad(vx, vy)
        jug.actualizar(dt)

    # Métodos que deben ser implementados por las subclases
    def actualizar_defensa(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        raise NotImplementedError

    def actualizar_mediocampistas(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        raise NotImplementedError

    def actualizar_delanteros(self, equipo, equipo_rival, pelota, dt, jugador_con_balon):
        raise NotImplementedError