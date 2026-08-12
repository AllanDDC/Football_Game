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


# ------------------------------------------------------------
#  Funciones básicas de distancia
# ------------------------------------------------------------
def distancia(ax, ay, bx, by):
    """Calcula la distancia euclidiana entre dos puntos."""
    return math.hypot(ax - bx, ay - by)


def distancia_objetos(obj_a, obj_b):
    """Calcula la distancia entre dos objetos que tengan atributos x e y."""
    return math.hypot(obj_a.x - obj_b.x, obj_a.y - obj_b.y)


# ------------------------------------------------------------
#  Colisiones y resolución
# ------------------------------------------------------------
def circulos_colisionan(a, b):
    """
    Detecta si dos círculos (objetos con x, y, radio) colisionan.
    Devuelve True si la distancia entre centros es menor que la suma de radios.
    """
    dist = distancia_objetos(a, b)
    return dist < (a.radio + b.radio)


def resolver_colision_entre_jugadores(j1, j2):
    """
    Separa dos jugadores que se solapan, aplicando un factor de suavizado
    y amortiguación para reducir vibraciones.
    """
    dx = j2.x - j1.x
    dy = j2.y - j1.y
    dist = math.hypot(dx, dy)

    if dist == 0:
        j1.x -= random.uniform(-2, 2)
        j1.y -= random.uniform(-2, 2)
        j2.x += random.uniform(-2, 2)
        j2.y += random.uniform(-2, 2)
        return

    overlap = (j1.radio + j2.radio) - dist
    if overlap <= 0:
        return

    nx = dx / dist
    ny = dy / dist

    factor = 0.3
    separacion = overlap * factor + 1.5

    j1.x -= nx * separacion
    j1.y -= ny * separacion
    j2.x += nx * separacion
    j2.y += ny * separacion

    j1.x = max(j1.radio, min(SCREEN_WIDTH - j1.radio, j1.x))
    j1.y = max(j1.radio, min(SCREEN_HEIGHT - j1.radio, j1.y))
    j2.x = max(j2.radio, min(SCREEN_WIDTH - j2.radio, j2.x))
    j2.y = max(j2.radio, min(SCREEN_HEIGHT - j2.radio, j2.y))

    j1.vx *= 0.75
    j1.vy *= 0.75
    j2.vx *= 0.75
    j2.vy *= 0.75


def resolver_colision_pelota_jugador(pelota, jugador):
    """
    Si la pelota colisiona con un jugador que no la tiene,
    rebota con una pequeña pérdida de energía y separación suave.
    """
    if pelota.pegada:
        return
    if jugador.tiene_balon:
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

    separacion = (jugador.radio + pelota.radio) - dist + 2.0
    pelota.x += nx * separacion
    pelota.y += ny * separacion

    velocidad = math.hypot(pelota.vx, pelota.vy)
    if velocidad > 10:
        vn = pelota.vx * nx + pelota.vy * ny
        if vn < 0:
            pelota.vx -= 2 * vn * nx * 0.6
            pelota.vy -= 2 * vn * ny * 0.6

    aplicar_limites_campo(pelota)


# ------------------------------------------------------------
#  Movimiento y límites
# ------------------------------------------------------------
def mover_hacia(origen, destino, velocidad, dt):
    """
    Calcula el vector de velocidad (vx, vy) que mueve 'origen' hacia 'destino'
    a la velocidad dada, respetando el paso temporal dt.
    Devuelve (vx, vy) como tupla.
    """
    dx = destino.x - origen.x
    dy = destino.y - origen.y
    dist = math.hypot(dx, dy)

    if dist == 0:
        return (0.0, 0.0)

    vx = (dx / dist) * velocidad
    vy = (dy / dist) * velocidad
    return (vx, vy)


def aplicar_limites_campo(entidad):
    """
    Aplica los límites del campo a una entidad (jugador o pelota) que tenga
    x, y y radio.
    """
    entidad.x = max(entidad.radio, min(SCREEN_WIDTH - entidad.radio, entidad.x))
    entidad.y = max(entidad.radio, min(SCREEN_HEIGHT - entidad.radio, entidad.y))


def esta_dentro_del_campo(x, y, radio):
    """Devuelve True si una entidad con centro (x,y) y radio dado está completamente dentro del campo."""
    if x - radio < 0 or x + radio > SCREEN_WIDTH:
        return False
    if y - radio < 0 or y + radio > SCREEN_HEIGHT:
        return False
    return True


def distancia_a_porteria(jugador, lado):
    """
    Calcula la distancia desde un jugador hasta el centro de la portería rival.
    lado = 'left' o 'right'.
    """
    if lado == 'left':
        porteria_x = 0
        porteria_y = SCREEN_HEIGHT / 2
    else:
        porteria_x = SCREEN_WIDTH
        porteria_y = SCREEN_HEIGHT / 2
    return distancia(jugador.x, jugador.y, porteria_x, porteria_y)


# ------------------------------------------------------------
#  Control de balón (conducción y recogida)
# ------------------------------------------------------------
def conducir_balon(jugador, pelota, dt):
    """
    Simula la conducción del balón: cuando el jugador se mueve,
    la pelota se adelanta en la dirección de movimiento.
    Solo se aplica si el jugador tiene la pelota y se está moviendo.
    """
    if not pelota.pegada or pelota.dueno != jugador:
        return

    velocidad = math.hypot(jugador.vx, jugador.vy)
    if velocidad < 10:
        # Si está quieto, la pelota se coloca justo delante
        pelota.x = jugador.x
        pelota.y = jugador.y - jugador.radio - pelota.radio - 4
        return

    # Dirección de movimiento (vector unitario)
    dx = jugador.vx / velocidad
    dy = jugador.vy / velocidad

    # Distancia de conducción: proporcional a la velocidad
    distancia_conduccion = 10 + velocidad * 0.03
    pelota.x = jugador.x + dx * distancia_conduccion
    pelota.y = jugador.y + dy * distancia_conduccion

    # Asegurar que la pelota no se salga del campo
    pelota.x = max(pelota.radio, min(SCREEN_WIDTH - pelota.radio, pelota.x))
    pelota.y = max(pelota.radio, min(SCREEN_HEIGHT - pelota.radio, pelota.y))


def intentar_recoger_balon(jugador, pelota):
    """
    Verifica si un jugador puede recoger la pelota.
    Condiciones:
      - La pelota NO está pegada a nadie.
      - La distancia entre jugador y pelota es menor que (radio_jugador + radio_pelota + margen).
      - El jugador no tiene ya el balón.
    Si se cumple, la pelota se adhiere al jugador.
    """
    if pelota.pegada:
        return False
    if jugador.tiene_balon:
        return False

    dist = distancia_objetos(jugador, pelota)
    umbral = jugador.radio + pelota.radio + 2.0

    if dist <= umbral:
        jugador.recoger_balon(pelota)
        return True
    return False


# ------------------------------------------------------------
#  Probabilidades de regate y robo (con estadísticas y fatiga)
# ------------------------------------------------------------
def probabilidad_regate(atacante_stats, defensor_stats):
    """
    Calcula la probabilidad de que el atacante supere al defensor en un 1vs1.
    Usa las estadísticas de regate y robo, y los factores de fatiga.
    """
    if atacante_stats is None or defensor_stats is None:
        return 0.5

    ataque = atacante_stats.regate
    defensa = defensor_stats.robo
    if ataque + defensa == 0:
        return 0.5

    prob = ataque / (ataque + defensa)

    factor_fatiga_atacante = 1.0 - (atacante_stats.fatiga / 200.0)  # máximo 50% de reducción
    factor_fatiga_defensor = 1.0 + (defensor_stats.fatiga / 200.0)  # máximo +50%

    prob *= factor_fatiga_atacante
    prob *= factor_fatiga_defensor

    return max(0.1, min(0.9, prob))


def probabilidad_robo(defensor_stats, atacante_stats):
    """
    Probabilidad de que el defensor robe el balón al atacante.
    Es la inversa de la probabilidad de regate del atacante.
    """
    return 1.0 - probabilidad_regate(atacante_stats, defensor_stats)


def intentar_regate(atacante, defensor):
    """
    Ejecuta un regate entre atacante y defensor.
    Devuelve True si el regate tiene éxito (el atacante supera al defensor).
    """
    atacante_stats = getattr(atacante, 'stats', None)
    defensor_stats = getattr(defensor, 'stats', None)

    if atacante_stats is None or defensor_stats is None:
        return random.random() < 0.5

    prob = probabilidad_regate(atacante_stats, defensor_stats)
    return random.random() < prob


def intentar_robo(defensor, atacante):
    """
    Determina si el defensor logra robar el balón al atacante.
    Se llama cuando colisionan.
    """
    defensor_stats = getattr(defensor, 'stats', None)
    atacante_stats = getattr(atacante, 'stats', None)

    if defensor_stats is None or atacante_stats is None:
        return random.random() < 0.3

    prob = probabilidad_robo(defensor_stats, atacante_stats)
    return random.random() < prob


# ------------------------------------------------------------
#  Fin del módulo
# ------------------------------------------------------------