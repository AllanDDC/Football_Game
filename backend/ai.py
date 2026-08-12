# backend/ai.py
"""
Módulo de inteligencia artificial para jugadores no controlados.
Ahora utiliza un sistema táctico modular, delegando el comportamiento
defensivo, de mediocampo y ofensivo en las clases de táctica.
"""

import math
import random
from .config import (
    PLAYER_SPEED,
    SPRINT_MULTIPLIER,
    AI_CHASE_DISTANCE,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    PLAYER_RADIUS,
    FATIGUE_RATE,
    GOAL_HEIGHT,
    GOAL_DEPTH
)
from .physics import (
    mover_hacia,
    distancia_objetos,
    aplicar_limites_campo,
    conducir_balon,
    intentar_regate,
    intentar_robo,
    probabilidad_regate,
    probabilidad_robo
)
from .tactics import TACTICAS_CLASES
from .tactics.tiki_taka import TikiTaka  # fallback
from .player_stats import PlayerStats
from .ball_control import ejecutar_pase, intentar_recibir, ejecutar_tiro


# ------------------------------------------------------------
#  Funciones auxiliares (compartidas con las tácticas)
# ------------------------------------------------------------
def _posicion_base(indice, formacion):
    """Retorna la posición base (x, y) en píxeles para un jugador dado su índice y formación."""
    from .tactics.base import FORMACION_LOCAL, FORMACION_RIVAL
    if indice < len(formacion):
        fx, fy = formacion[indice]
        return (fx * SCREEN_WIDTH, fy * SCREEN_HEIGHT)
    return (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)


def _get_velocidad_efectiva(jug, factor=0.5, sprint=False):
    """
    Calcula la velocidad efectiva del jugador considerando estadísticas, fatiga y sprint.
    Esta función se usa tanto desde ai.py como desde las tácticas.
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
#  Función principal de actualización de IA (usa tácticas)
# ------------------------------------------------------------
def actualizar_ia(equipo_local, equipo_rival, pelota, dt, tiempo_partido=90):
    # Identificar jugador humano (solo para referencia, no se usa en tácticas)
    jugador_humano = None
    jugador_con_balon = None

    for jug in equipo_local.jugadores:
        if jug.es_controlado:
            jugador_humano = jug
        if jug.tiene_balon:
            jugador_con_balon = jug

    for jug in equipo_rival.jugadores:
        if jug.tiene_balon:
            jugador_con_balon = jug

    # Asegurar estadísticas
    _asegurar_stats(equipo_local)
    _asegurar_stats(equipo_rival)

    # Asegurar que cada equipo tenga su objeto de táctica
    for equipo in [equipo_local, equipo_rival]:
        if not hasattr(equipo, 'tactica_obj'):
            # Obtener el nombre de la táctica actual (si no existe, usar "tiki_taka")
            tactica_nombre = getattr(equipo, 'tactica_actual', 'tiki_taka')
            # Obtener la clase de táctica del registro
            clase_tactica = TACTICAS_CLASES.get(tactica_nombre)
            if clase_tactica is None:
                clase_tactica = TikiTaka  # fallback
            equipo.tactica_obj = clase_tactica()
            # También aseguramos que el equipo tenga el nombre de la táctica actual
            equipo.tactica_actual = tactica_nombre

    # Actualizar cada equipo usando su táctica
    _actualizar_equipo_con_tactica(equipo_local, equipo_rival, pelota, dt, jugador_con_balon)
    _actualizar_equipo_con_tactica(equipo_rival, equipo_local, pelota, dt, jugador_con_balon)

    # Actualizar porteros (independiente de táctica)
    _actualizar_portero(equipo_local, 'left', dt, pelota)
    _actualizar_portero(equipo_rival, 'right', dt, pelota)

    # Aplicar fatiga
    _aplicar_cansancio(equipo_local, dt)
    _aplicar_cansancio(equipo_rival, dt)

    # Conducción del balón
    if jugador_con_balon is not None and jugador_con_balon.tiene_balon:
        conducir_balon(jugador_con_balon, pelota, dt)


def _actualizar_equipo_con_tactica(equipo, equipo_rival, pelota, dt, jugador_con_balon):
    """
    Aplica los métodos de la táctica al equipo: defensas, mediocampistas y delanteros.
    """
    tactica = equipo.tactica_obj
    # Actualizar defensas (índices 1-4)
    tactica.actualizar_defensa(equipo, equipo_rival, pelota, dt, jugador_con_balon)
    # Actualizar mediocampistas (índices 5-8)
    tactica.actualizar_mediocampistas(equipo, equipo_rival, pelota, dt, jugador_con_balon)
    # Actualizar delanteros (índices 9-10)
    tactica.actualizar_delanteros(equipo, equipo_rival, pelota, dt, jugador_con_balon)


# ------------------------------------------------------------
#  Portero (genérico)
# ------------------------------------------------------------
def _actualizar_portero(equipo, lado, dt, pelota):
    if not equipo.jugadores:
        return
    portero = equipo.jugadores[0]
    if hasattr(portero, 'expulsado') and portero.expulsado:
        return

    velocidad_base = PLAYER_SPEED * 0.25
    if hasattr(portero, 'stats'):
        stat_vel = portero.stats.velocidad / 100.0
        velocidad_base = PLAYER_SPEED * (0.15 + stat_vel * 0.2)
        if portero.stats.fatiga > 50:
            factor_fatiga = 1.0 - (portero.stats.fatiga - 50) / 150.0
            velocidad_base *= max(0.3, factor_fatiga)

    base_x = 50 if lado == 'left' else SCREEN_WIDTH - 50
    target_y = pelota.y
    min_y = SCREEN_HEIGHT // 2 - GOAL_HEIGHT // 2 + 20
    max_y = SCREEN_HEIGHT // 2 + GOAL_HEIGHT // 2 - 20
    target_y = max(min_y, min(max_y, target_y))

    dy = target_y - portero.y
    if abs(dy) > 5:
        vy = dy * 0.04
        max_vel = velocidad_base * 0.5
        vy = max(-max_vel, min(max_vel, vy))
        portero.establecer_velocidad(0, vy)
    else:
        portero.establecer_velocidad(0, 0)

    portero.x = base_x
    portero.actualizar(dt)
    aplicar_limites_campo(portero)


# ------------------------------------------------------------
#  Fatiga
# ------------------------------------------------------------
def _aplicar_cansancio(equipo, dt):
    for jug in equipo.jugadores:
        if not hasattr(jug, 'stats'):
            continue
        velocidad_actual = math.hypot(jug.vx, jug.vy)
        sprint = getattr(jug, 'sprint', False)
        if velocidad_actual > 30:
            jug.stats.aplicar_cansancio(dt, velocidad_actual, sprint=sprint)
        else:
            jug.stats.recuperar_cansancio(dt * 0.5)


# ------------------------------------------------------------
#  Asegurar estadísticas
# ------------------------------------------------------------
def _asegurar_stats(equipo):
    for jug in equipo.jugadores:
        if not hasattr(jug, 'stats') or jug.stats is None:
            nombre = f"{equipo.nombre}_{jug.numero}"
            edad = random.randint(18, 35)
            stats_override = {
                "velocidad": random.randint(50, 85),
                "resistencia": random.randint(50, 85),
                "pase": random.randint(40, 80),
                "regate": random.randint(40, 80),
                "robo": random.randint(40, 80),
                "tiro": random.randint(40, 80)
            }
            jug.stats = PlayerStats(nombre, edad, stats_override)
            if jug.numero == 0:
                jug.stats.stats_base["robo"] = 90
                jug.stats.stats_base["pase"] = 50
            elif jug.numero < 5:
                jug.stats.stats_base["robo"] += 10
            elif jug.numero < 9:
                jug.stats.stats_base["pase"] += 10
            else:
                jug.stats.stats_base["tiro"] += 10


# ------------------------------------------------------------
#  Resolver contacto (llamado desde game.py)
# ------------------------------------------------------------
def resolver_contacto_jugadores(jug1, jug2):
    if jug1.tiene_balon and jug2.equipo != jug1.equipo:
        if intentar_robo(jug2, jug1):
            if jug1.tiene_balon:
                jug1.tiene_balon = False
                jug1.pelota.dueno = None
                jug1.pelota.pegada = False
                angulo = random.uniform(0, 2 * math.pi)
                velocidad = random.uniform(50, 150)
                jug1.pelota.vx = math.cos(angulo) * velocidad
                jug1.pelota.vy = math.sin(angulo) * velocidad
                if hasattr(jug2, 'stats'):
                    jug2.stats.registrar_robo()
                if hasattr(jug1, 'stats'):
                    jug1.stats.registrar_regate(False)
                return True
    elif jug2.tiene_balon and jug1.equipo != jug2.equipo:
        if intentar_robo(jug1, jug2):
            if jug2.tiene_balon:
                jug2.tiene_balon = False
                jug2.pelota.dueno = None
                jug2.pelota.pegada = False
                angulo = random.uniform(0, 2 * math.pi)
                velocidad = random.uniform(50, 150)
                jug2.pelota.vx = math.cos(angulo) * velocidad
                jug2.pelota.vy = math.sin(angulo) * velocidad
                if hasattr(jug1, 'stats'):
                    jug1.stats.registrar_robo()
                if hasattr(jug2, 'stats'):
                    jug2.stats.registrar_regate(False)
                return True
    return False


def calcular_precision_pase(jugador, distancia_pase):
    if not hasattr(jugador, 'stats'):
        return 0.7
    stat_pase = jugador.stats.pase / 100.0
    factor_distancia = 1.0 - min(1.0, distancia_pase / 500.0)
    factor_fatiga = 1.0 - (jugador.stats.fatiga / 200.0)
    precision = (stat_pase * 0.6 + 0.4) * factor_distancia * factor_fatiga
    return max(0.1, min(0.95, precision))