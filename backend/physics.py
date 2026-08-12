# backend/physics.py
import math
import random
from .config import (
    PLAYER_RADIUS,
    BALL_RADIUS,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    AI_CHASE_DISTANCE,
    PLAYER_SPEED,
    GOAL_HEIGHT,
    GOAL_DEPTH
)


def distancia(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


def distancia_objetos(obj_a, obj_b):
    return math.hypot(obj_a.x - obj_b.x, obj_a.y - obj_b.y)


def circulos_colisionan(a, b):
    """Detecta colisión sin margen extra."""
    dist = distancia_objetos(a, b)
    return dist < (a.radio + b.radio)


def resolver_colision_entre_jugadores(j1, j2):
    """Separa jugadores con factor suave y margen mínimo."""
    dx = j2.x - j1.x
    dy = j2.y - j1.y
    dist = math.hypot(dx, dy)
    if dist == 0:
        return
    overlap = (j1.radio + j2.radio) - dist
    if overlap <= 0:
        return
    nx = dx / dist
    ny = dy / dist
    factor = 0.2
    separacion = overlap * factor + 0.5
    j1.x -= nx * separacion
    j1.y -= ny * separacion
    j2.x += nx * separacion
    j2.y += ny * separacion
    j1.vx *= 0.9
    j1.vy *= 0.9
    j2.vx *= 0.9
    j2.vy *= 0.9


def resolver_colision_pelota_jugador(pelota, jugador):
    if pelota.pegada or jugador.tiene_balon:
        return
    dist = distancia_objetos(pelota, jugador)
    if dist > jugador.radio + pelota.radio:
        return
    dx = pelota.x - jugador.x
    dy = pelota.y - jugador.y
    if dist == 0:
        dx, dy = random.uniform(-1, 1), random.uniform(-1, 1)
        dist = math.hypot(dx, dy)
    nx = dx / dist
    ny = dy / dist
    separacion = (jugador.radio + pelota.radio) - dist + 1.0
    pelota.x += nx * separacion
    pelota.y += ny * separacion
    velocidad = math.hypot(pelota.vx, pelota.vy)
    if velocidad > 10:
        vn = pelota.vx * nx + pelota.vy * ny
        if vn < 0:
            pelota.vx -= 2 * vn * nx * 0.6
            pelota.vy -= 2 * vn * ny * 0.6
    aplicar_limites_campo(pelota)


def mover_hacia(origen, destino, velocidad, dt):
    dx = destino.x - origen.x
    dy = destino.y - origen.y
    dist = math.hypot(dx, dy)
    if dist == 0:
        return (0.0, 0.0)
    vx = (dx / dist) * velocidad
    vy = (dy / dist) * velocidad
    return (vx, vy)


def aplicar_limites_campo(entidad):
    entidad.x = max(entidad.radio, min(SCREEN_WIDTH - entidad.radio, entidad.x))
    entidad.y = max(entidad.radio, min(SCREEN_HEIGHT - entidad.radio, entidad.y))


def esta_dentro_del_campo(x, y, radio):
    if x - radio < 0 or x + radio > SCREEN_WIDTH:
        return False
    if y - radio < 0 or y + radio > SCREEN_HEIGHT:
        return False
    return True


def distancia_a_porteria(jugador, lado):
    if lado == 'left':
        porteria_x = 0
        porteria_y = SCREEN_HEIGHT / 2
    else:
        porteria_x = SCREEN_WIDTH
        porteria_y = SCREEN_HEIGHT / 2
    return distancia(jugador.x, jugador.y, porteria_x, porteria_y)


def conducir_balon(jugador, pelota, dt):
    if not pelota.pegada or pelota.dueno != jugador:
        return
    velocidad = math.hypot(jugador.vx, jugador.vy)
    if velocidad < 10:
        pelota.x = jugador.x
        pelota.y = jugador.y - jugador.radio - pelota.radio - 4
        return
    dx = jugador.vx / velocidad
    dy = jugador.vy / velocidad
    distancia_conduccion = 8 + velocidad * 0.025
    pelota.x = jugador.x + dx * distancia_conduccion
    pelota.y = jugador.y + dy * distancia_conduccion
    pelota.x = max(pelota.radio, min(SCREEN_WIDTH - pelota.radio, pelota.x))
    pelota.y = max(pelota.radio, min(SCREEN_HEIGHT - pelota.radio, pelota.y))


def intentar_recoger_balon(jugador, pelota):
    if pelota.pegada or jugador.tiene_balon:
        return False
    dist = distancia_objetos(jugador, pelota)
    umbral = jugador.radio + pelota.radio + 2.0
    if dist <= umbral:
        jugador.recoger_balon(pelota)
        return True
    return False


def probabilidad_regate(atacante_stats, defensor_stats):
    if atacante_stats is None or defensor_stats is None:
        return 0.5
    ataque = atacante_stats.regate
    defensa = defensor_stats.robo
    if ataque + defensa == 0:
        return 0.5
    prob = ataque / (ataque + defensa)
    factor_fatiga_atacante = 1.0 - (atacante_stats.fatiga / 200.0)
    factor_fatiga_defensor = 1.0 + (defensor_stats.fatiga / 200.0)
    prob *= factor_fatiga_atacante
    prob *= factor_fatiga_defensor
    return max(0.1, min(0.9, prob))


def probabilidad_robo(defensor_stats, atacante_stats):
    return 1.0 - probabilidad_regate(atacante_stats, defensor_stats)


def intentar_regate(atacante, defensor):
    atacante_stats = getattr(atacante, 'stats', None)
    defensor_stats = getattr(defensor, 'stats', None)
    if atacante_stats is None or defensor_stats is None:
        return random.random() < 0.5
    prob = probabilidad_regate(atacante_stats, defensor_stats)
    return random.random() < prob


def intentar_robo(defensor, atacante):
    """Robo solo si están realmente en contacto (distancia < radios)."""
    dist = distancia_objetos(defensor, atacante)
    if dist >= (defensor.radio + atacante.radio):
        return False
    defensor_stats = getattr(defensor, 'stats', None)
    atacante_stats = getattr(atacante, 'stats', None)
    if defensor_stats is None or atacante_stats is None:
        return random.random() < 0.3
    prob = probabilidad_robo(defensor_stats, atacante_stats)
    return random.random() < prob