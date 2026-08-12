# backend/ai.py
"""
Módulo de inteligencia artificial para jugadores no controlados.
Comportamientos mejorados: respeto de formaciones, presión en zona,
repliegue defensivo en bloque, y sprint en persecuciones.
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
from .tactics import (
    TACTICAS,
    obtener_distancia_presion,
    obtener_factor_posesion,
    obtener_factor_pase_largo,
    obtener_frecuencia_regate,
    obtener_profundidad_defensiva,
    obtener_altura_delanteros_defensiva,
    aplicar_tactica_a_equipo
)
from .player_stats import PlayerStats
from .ball_control import ejecutar_pase, intentar_recibir, ejecutar_tiro


# ------------------------------------------------------------
#  Posiciones base para formaciones (4-4-2 estándar)
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


def _posicion_base(indice, formacion):
    """Retorna la posición base (x, y) en píxeles para un jugador dado su índice y formación."""
    if indice < len(formacion):
        fx, fy = formacion[indice]
        return (fx * SCREEN_WIDTH, fy * SCREEN_HEIGHT)
    return (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)


def _get_velocidad_efectiva(jug, factor=0.5, sprint=False):
    """
    Calcula la velocidad efectiva del jugador considerando estadísticas, fatiga y sprint.
    Si sprint=True, se multiplica por SPRINT_MULTIPLIER (igual que el humano).
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
#  Función principal de actualización de IA
# ------------------------------------------------------------
def actualizar_ia(equipo_local, equipo_rival, pelota, dt, tiempo_partido=90):
    # Identificar jugadores clave
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

    # Aplicar tácticas si no existen
    if not hasattr(equipo_local, 'tactica_actual'):
        aplicar_tactica_a_equipo(equipo_local, "tiki_taka", pelota, dt)
    if not hasattr(equipo_rival, 'tactica_actual'):
        aplicar_tactica_a_equipo(equipo_rival, "catenaccio", pelota, dt)

    # Actualizar jugadores según su rol y posesión
    _actualizar_equipo_con_roles(equipo_local, equipo_rival, pelota, dt, jugador_con_balon, es_local=True)
    _actualizar_equipo_con_roles(equipo_rival, equipo_local, pelota, dt, jugador_con_balon, es_local=False)

    # Porteros
    _actualizar_portero(equipo_local, 'left', dt, pelota)
    _actualizar_portero(equipo_rival, 'right', dt, pelota)

    # Cansancio
    _aplicar_cansancio(equipo_local, dt)
    _aplicar_cansancio(equipo_rival, dt)

    # Conducción del balón
    if jugador_con_balon is not None and jugador_con_balon.tiene_balon:
        conducir_balon(jugador_con_balon, pelota, dt)


# ------------------------------------------------------------
#  Actualización de equipos con roles y lógica de posesión
# ------------------------------------------------------------
def _actualizar_equipo_con_roles(equipo, equipo_rival, pelota, dt, jugador_con_balon, es_local):
    """
    Actualiza cada jugador según su rol y si el equipo tiene la posesión.
    """
    tiene_posesion = jugador_con_balon is not None and jugador_con_balon.equipo == equipo.nombre
    tactica_nombre = getattr(equipo, 'tactica_actual', 'tiki_taka')
    tactica = TACTICAS.get(tactica_nombre, TACTICAS["tiki_taka"])
    profundidad = tactica.params.get("profundidad_defensiva", 0.5)
    altura_delanteros_def = obtener_altura_delanteros_defensiva(equipo)

    for i, jug in enumerate(equipo.jugadores):
        if jug.es_controlado:
            continue
        if hasattr(jug, 'expulsado') and jug.expulsado:
            continue
        if hasattr(jug, 'lesionado') and jug.lesionado:
            continue

        # Determinar rol según índice
        if i == 0:
            continue  # portero
        elif i < 5:
            rol = "defensa"
        elif i < 9:
            rol = "mediocampista"
        else:
            rol = "delantero"

        # Comportamiento según rol y posesión
        if rol == "defensa":
            _actualizar_defensa(jug, equipo, equipo_rival, pelota, dt, jugador_con_balon, es_local, tiene_posesion, profundidad)
        elif rol == "mediocampista":
            _actualizar_mediocampista(jug, equipo, equipo_rival, pelota, dt, jugador_con_balon, es_local, tiene_posesion, profundidad)
        else:  # delantero
            _actualizar_delantero(jug, equipo, equipo_rival, pelota, dt, jugador_con_balon, es_local, tiene_posesion, profundidad, altura_delanteros_def)


# ------------------------------------------------------------
#  Defensa: repliegue en bloque y presión selectiva
# ------------------------------------------------------------
def _actualizar_defensa(jug, equipo, equipo_rival, pelota, dt, jugador_con_balon, es_local, tiene_posesion, profundidad):
    """Defensa: retrocede en bloque, el más cercano presiona, los demás cierran espacios."""
    usar_sprint = False
    poseedor = None
    if jugador_con_balon is not None and jugador_con_balon.equipo != equipo.nombre:
        poseedor = jugador_con_balon
        dist = distancia_objetos(jug, poseedor)
        # Usar sprint solo si está cerca del poseedor y la fatiga lo permite
        if dist < 200 and dist > 50 and jug.stats.fatiga < 60:
            usar_sprint = True

    velocidad_base = _get_velocidad_efectiva(jug, factor=0.6, sprint=usar_sprint)
    bx, by = _posicion_base(jug.numero, FORMACION_LOCAL if es_local else FORMACION_RIVAL)

    if not tiene_posesion and poseedor is not None:
        # ---- EL RIVAL ATACA: REPLIEGUE EN BLOQUE ----
        porteria_x = 50 if es_local else SCREEN_WIDTH - 50
        # Profundidad: cuanto mayor, más atrás
        if es_local:
            bx = porteria_x + (bx - porteria_x) * (1 - profundidad * 0.7)
        else:
            bx = porteria_x - (porteria_x - bx) * (1 - profundidad * 0.7)

        # El defensa más cercano al poseedor sale a presionar (si está dentro de su zona)
        dist = distancia_objetos(jug, poseedor)
        # Solo presiona si está dentro de su área de influencia (radio 200)
        if dist < 180:
            vx, vy = mover_hacia(jug, poseedor, velocidad_base * 1.1, dt)
            jug.establecer_velocidad(vx, vy)
            jug.actualizar(dt)
            return

        # Si no presiona, se mueve a su posición defensiva, pero con tendencia a cerrar al centro
        # para reducir espacios entre defensas
        centro_y = SCREEN_HEIGHT / 2
        # Ajustar la Y para cerrar hacia el centro (efecto acordeón)
        diff_centro = by - centro_y
        by -= diff_centro * 0.3  # se acerca al centro un 30%

        destino = type('obj', (object,), {'x': bx, 'y': by})()
        if distancia_objetos(jug, destino) > 10:
            vx, vy = mover_hacia(jug, destino, velocidad_base * 0.8, dt)
            jug.establecer_velocidad(vx, vy)
            jug.actualizar(dt)
        else:
            jug.establecer_velocidad(0, 0)
            jug.actualizar(dt)
    else:
        # ---- EL EQUIPO TIENE EL BALÓN: SUBIR PARA APOYAR ----
        if es_local:
            bx += 50
        else:
            bx -= 50
        destino = type('obj', (object,), {'x': bx, 'y': by})()
        if distancia_objetos(jug, destino) > 10:
            vx, vy = mover_hacia(jug, destino, velocidad_base * 0.4, dt)
            jug.establecer_velocidad(vx, vy)
            jug.actualizar(dt)
        else:
            jug.establecer_velocidad(0, 0)
            jug.actualizar(dt)


# ------------------------------------------------------------
#  Mediocampista: presión en zona y repliegue
# ------------------------------------------------------------
def _actualizar_mediocampista(jug, equipo, equipo_rival, pelota, dt, jugador_con_balon, es_local, tiene_posesion, profundidad):
    """Mediocampista: presiona solo si el poseedor está en su zona, si no retrocede."""
    usar_sprint = False
    poseedor = None
    if jugador_con_balon is not None and jugador_con_balon.equipo != equipo.nombre:
        poseedor = jugador_con_balon
        dist = distancia_objetos(jug, poseedor)
        if dist < 250 and dist > 80 and jug.stats.fatiga < 65:
            usar_sprint = True

    velocidad_base = _get_velocidad_efectiva(jug, factor=0.7, sprint=usar_sprint)
    bx, by = _posicion_base(jug.numero, FORMACION_LOCAL if es_local else FORMACION_RIVAL)

    if tiene_posesion:
        # ---- EQUIPO CON BALÓN: DESMARQUE ----
        if jug.tiene_balon:
            porteria_x = SCREEN_WIDTH if es_local else 0
            porteria_y = SCREEN_HEIGHT // 2
            destino = type('obj', (object,), {'x': porteria_x, 'y': porteria_y})()
            vx, vy = mover_hacia(jug, destino, velocidad_base * 0.9, dt)
            jug.establecer_velocidad(vx, vy)
            jug.actualizar(dt)
            if jug.stats.fatiga < 70 and random.random() < 0.04:
                _intentar_pase_ia(jug, equipo, pelota)
            return

        # Sin balón: moverse para ofrecer pase
        if jugador_con_balon is not None and jugador_con_balon.equipo == equipo.nombre:
            angulo = math.atan2(jug.y - jugador_con_balon.y, jug.x - jugador_con_balon.x)
            angulo += random.uniform(-0.8, 0.8)
            radio = 120 + random.uniform(0, 30)
            destino_x = jugador_con_balon.x + math.cos(angulo) * radio
            destino_y = jugador_con_balon.y + math.sin(angulo) * radio
            destino_x = max(PLAYER_RADIUS, min(SCREEN_WIDTH - PLAYER_RADIUS, destino_x))
            destino_y = max(PLAYER_RADIUS, min(SCREEN_HEIGHT - PLAYER_RADIUS, destino_y))
            destino = type('obj', (object,), {'x': destino_x, 'y': destino_y})()
            if distancia_objetos(jug, destino) > 15:
                vx, vy = mover_hacia(jug, destino, velocidad_base * 0.8, dt)
                jug.establecer_velocidad(vx, vy)
                jug.actualizar(dt)
                return

        destino = type('obj', (object,), {'x': bx, 'y': by})()
        if distancia_objetos(jug, destino) > 15:
            vx, vy = mover_hacia(jug, destino, velocidad_base * 0.4, dt)
            jug.establecer_velocidad(vx, vy)
            jug.actualizar(dt)
    else:
        # ---- RIVAL CON BALÓN: PRESIÓN EN ZONA O REPLIEGUE ----
        if poseedor is not None:
            dist = distancia_objetos(jug, poseedor)
            # Solo presiona si el poseedor está en su zona de influencia (cerca de su posición base)
            if dist < 250:
                vx, vy = mover_hacia(jug, poseedor, velocidad_base * 1.0, dt)
                jug.establecer_velocidad(vx, vy)
                jug.actualizar(dt)
                return

        # Retroceder a posición defensiva (más atrás)
        if es_local:
            bx = max(PLAYER_RADIUS, bx - 40 * (1 - profundidad))
        else:
            bx = min(SCREEN_WIDTH - PLAYER_RADIUS, bx + 40 * (1 - profundidad))
        destino = type('obj', (object,), {'x': bx, 'y': by})()
        if distancia_objetos(jug, destino) > 15:
            vx, vy = mover_hacia(jug, destino, velocidad_base * 0.6, dt)
            jug.establecer_velocidad(vx, vy)
            jug.actualizar(dt)


# ------------------------------------------------------------
#  Delantero: presión en campo propio, ataque en campo rival
# ------------------------------------------------------------
def _actualizar_delantero(jug, equipo, equipo_rival, pelota, dt, jugador_con_balon, es_local, tiene_posesion, profundidad, altura_delanteros_def):
    """Delantero: presiona al poseedor si está en campo propio, si no se mantiene arriba."""
    usar_sprint = False
    poseedor = None
    if jugador_con_balon is not None and jugador_con_balon.equipo != equipo.nombre:
        poseedor = jugador_con_balon
        dist = distancia_objetos(jug, poseedor)
        if dist < 200 and dist > 80 and jug.stats.fatiga < 60:
            usar_sprint = True

    velocidad_base = _get_velocidad_efectiva(jug, factor=0.8, sprint=usar_sprint)
    porteria_x = SCREEN_WIDTH if es_local else 0
    porteria_y = SCREEN_HEIGHT // 2

    if tiene_posesion:
        # ---- EQUIPO CON BALÓN: BUSCAR GOL ----
        if jug.tiene_balon:
            destino = type('obj', (object,), {'x': porteria_x, 'y': porteria_y})()
            vx, vy = mover_hacia(jug, destino, velocidad_base * 1.0, dt)
            jug.establecer_velocidad(vx, vy)
            jug.actualizar(dt)
            if distancia_objetos(jug, destino) < 250 and random.random() < 0.025:
                ejecutar_tiro(jug, pelota)
            return

        # Sin balón: desmarcarse en área rival
        angulo = random.uniform(-1.2, 1.2)
        radio = 80 + random.uniform(0, 50)
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
        # ---- RIVAL CON BALÓN: PRESIÓN EN CAMPO PROPIO ----
        # Si el poseedor está en nuestro campo (mitad defensiva), presionar
        if poseedor is not None:
            # Determinar si está en campo propio
            if (es_local and poseedor.x < SCREEN_WIDTH * 0.6) or (not es_local and poseedor.x > SCREEN_WIDTH * 0.4):
                dist = distancia_objetos(jug, poseedor)
                if dist < 200 and jug.stats.fatiga < 70:
                    vx, vy = mover_hacia(jug, poseedor, velocidad_base * 0.8, dt)
                    jug.establecer_velocidad(vx, vy)
                    jug.actualizar(dt)
                    return

        # Si no presiona, retroceder según altura_delanteros_def (0=arriba, 1=abajo)
        retroceso_x = porteria_x + (SCREEN_WIDTH // 2 - porteria_x) * (1 - altura_delanteros_def * 0.7)
        retroceso_y = porteria_y + random.uniform(-50, 50)
        destino = type('obj', (object,), {'x': retroceso_x, 'y': retroceso_y})()
        if distancia_objetos(jug, destino) > 15:
            vx, vy = mover_hacia(jug, destino, velocidad_base * 0.5, dt)
            jug.establecer_velocidad(vx, vy)
            jug.actualizar(dt)


# ------------------------------------------------------------
#  Portero (mejorado)
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
#  Pase entre bots (IA)
# ------------------------------------------------------------
def _intentar_pase_ia(jug, equipo, pelota):
    if not jug.tiene_balon:
        return
    mejor = None
    mejor_dist = float('inf')
    for comp in equipo.jugadores:
        if comp == jug or comp.tiene_balon:
            continue
        dist = distancia_objetos(jug, comp)
        if 50 < dist < 200 and dist < mejor_dist:
            mejor_dist = dist
            mejor = comp
    if mejor is not None and random.random() < 0.4:
        ejecutar_pase(jug, mejor, pelota, es_largo=False)


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