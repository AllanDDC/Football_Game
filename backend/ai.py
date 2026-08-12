# backend/ai.py
"""
Módulo de inteligencia artificial para jugadores no controlados.
Ahora utiliza un sistema táctico modular para la fase defensiva
y un sistema de construcción de juego (build-up) para la fase ofensiva.
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
# Importar desde tactics.base para evitar circularidad
from .tactics.base import _posicion_base, _get_velocidad_efectiva
from .player_stats import PlayerStats
from .ball_control import ejecutar_pase, intentar_recibir, ejecutar_tiro
# Importar build-up manager
from .build_up import BuildUpManager


# ------------------------------------------------------------
#  Función principal de actualización de IA (usa tácticas y build-up)
# ------------------------------------------------------------
def actualizar_ia(equipo_local, equipo_rival, pelota, dt, tiempo_partido=90):
    # Importar TACTICAS_CLASES aquí para evitar circularidad
    from .tactics import TACTICAS_CLASES
    from .tactics.tiki_taka import TikiTaka  # fallback

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
            tactica_nombre = getattr(equipo, 'tactica_actual', 'tiki_taka')
            clase_tactica = TACTICAS_CLASES.get(tactica_nombre)
            if clase_tactica is None:
                clase_tactica = TikiTaka
            equipo.tactica_obj = clase_tactica()
            equipo.tactica_actual = tactica_nombre

    # Actualizar cada equipo:
    # - Si tiene la pelota: usar build-up (movimientos ofensivos)
    # - Si no tiene la pelota: usar táctica defensiva (presión, repliegue)
    _actualizar_equipo_con_buildup_o_tactica(
        equipo_local, equipo_rival, pelota, dt, jugador_con_balon, es_local=True
    )
    _actualizar_equipo_con_buildup_o_tactica(
        equipo_rival, equipo_local, pelota, dt, jugador_con_balon, es_local=False
    )

    # Actualizar porteros (independiente de táctica)
    _actualizar_portero(equipo_local, 'left', dt, pelota)
    _actualizar_portero(equipo_rival, 'right', dt, pelota)

    # Aplicar fatiga
    _aplicar_cansancio(equipo_local, dt)
    _aplicar_cansancio(equipo_rival, dt)

    # Conducción del balón
    if jugador_con_balon is not None and jugador_con_balon.tiene_balon:
        conducir_balon(jugador_con_balon, pelota, dt)


def _actualizar_equipo_con_buildup_o_tactica(equipo, equipo_rival, pelota, dt, jugador_con_balon, es_local):
    """
    Decide si aplicar build-up (ofensivo) o táctica defensiva.
    """
    tactica = equipo.tactica_obj
    poseedor_propio = (jugador_con_balon is not None and
                       jugador_con_balon.equipo == equipo.nombre)

    if poseedor_propio:
        # ---- FASE OFENSIVA: usar build-up ----
        # Inicializar BuildUpManager si no existe
        if not hasattr(equipo, 'build_up_manager'):
            equipo.build_up_manager = BuildUpManager(equipo)

        # Definir función de velocidad para el manager
        def get_velocidad(jug, factor, sprint):
            return _get_velocidad_efectiva(jug, factor, sprint)

        # Aplicar estrategias ofensivas a todos los jugadores
        equipo.build_up_manager.actualizar(
            equipo_rival, pelota, dt, jugador_con_balon, get_velocidad
        )
        # Nota: el manager ya mueve a los jugadores, así que no necesitamos
        # llamar a las funciones de la táctica para estos jugadores.
        # Sin embargo, los jugadores que no fueron movidos por el manager
        # (por ejemplo, porque ninguna estrategia aplicó) aún deben tener
        # un movimiento base. Para eso, podemos llamar a la táctica ofensiva
        # (desmarque básico) solo para esos jugadores.
        # Por simplicidad, aquí delegamos completamente en el manager.
        # Si el manager no mueve a algún jugador, se quedará quieto.
        # Podríamos añadir una estrategia de respaldo en el manager.
        # En la implementación actual del manager, si ninguna estrategia
        # aplica, el jugador no se mueve. Para evitar esto, añadimos un
        # movimiento de "apoyo básico" dentro del manager. Pero eso ya está
        # en las estrategias (bandas, pasillos, etc.) que cubren todos los roles.
        # Así que está bien.
        return

    # ---- FASE DEFENSIVA: usar táctica ----
    # Primero, actualizar defensas (índices 1-4)
    tactica.actualizar_defensa(equipo, equipo_rival, pelota, dt, jugador_con_balon)
    # Actualizar mediocampistas (índices 5-8)
    tactica.actualizar_mediocampistas(equipo, equipo_rival, pelota, dt, jugador_con_balon)
    # Actualizar delanteros (índices 9-10)
    tactica.actualizar_delanteros(equipo, equipo_rival, pelota, dt, jugador_con_balon)


# ------------------------------------------------------------
#  Decisión de sprint para bots (usada por tácticas y build-up)
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