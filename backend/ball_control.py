# backend/ball_control.py
"""
Módulo especializado en el control del balón.
VELOCIDADES REDUCIDAS 200 VECES con respecto a las originales
para que la pelota sea perfectamente visible.
"""

import math
import random
from .config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    PLAYER_RADIUS, BALL_RADIUS,
    PLAYER_SPEED
)
from .physics import (
    distancia_objetos,
    mover_hacia,
    aplicar_limites_campo,
    conducir_balon
)
from .player_stats import PlayerStats


# ------------------------------------------------------------
#  Funciones de pase
# ------------------------------------------------------------
def calcular_precision_pase(pasador, distancia, es_pase_largo=False):
    if not hasattr(pasador, 'stats'):
        return 0.7
    stat_pase = pasador.stats.pase / 100.0
    factor_distancia = 1.0 - min(1.0, distancia / 600.0)
    factor_fatiga = 1.0 - (pasador.stats.fatiga / 200.0)
    if es_pase_largo:
        factor_largo = 0.8 + 0.2 * stat_pase
    else:
        factor_largo = 1.0
    precision = (0.3 + 0.7 * stat_pase) * factor_distancia * factor_fatiga * factor_largo
    return max(0.1, min(0.95, precision))


def ejecutar_pase(pasador, receptor, pelota, es_largo=False):
    """
    Ejecuta un pase con velocidades extremadamente lentas.
    """
    if receptor:
        distancia = distancia_objetos(pasador, receptor)
    else:
        distancia = random.uniform(100, 300)

    precision = calcular_precision_pase(pasador, distancia, es_largo)
    exito = random.random() < precision

    if hasattr(pasador, 'stats'):
        pasador.stats.registrar_pase(exito)

    if exito:
        if receptor:
            # --- VELOCIDAD 200 VECES MÁS LENTA ---
            # Pase corto: 0.002 - 0.0035 px/s
            # Pase largo: 0.003 - 0.005 px/s
            if es_largo:
                velocidad_base = (60 + 40 * (1 - precision)) / 200.0
            else:
                velocidad_base = (40 + 30 * (1 - precision)) / 200.0

            dx = receptor.x - pasador.x
            dy = receptor.y - pasador.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                pelota.vx = (dx / dist) * velocidad_base
                pelota.vy = (dy / dist) * velocidad_base
                pelota.x = pasador.x + (dx / dist) * (pasador.radio + pelota.radio + 10)
                pelota.y = pasador.y + (dy / dist) * (pasador.radio + pelota.radio + 10)
            else:
                pelota.vx, pelota.vy = 0, -velocidad_base
                pelota.x = pasador.x
                pelota.y = pasador.y - pasador.radio - pelota.radio - 10

            if es_largo:
                pelota.vy -= 0.1  # efecto de arco mínimo
        else:
            # Pase al espacio: 0.0015 - 0.0035 px/s
            angulo = random.uniform(0, 2 * math.pi)
            velocidad = (30 + random.uniform(0, 40)) / 200.0
            pelota.vx = math.cos(angulo) * velocidad
            pelota.vy = math.sin(angulo) * velocidad
            pelota.x = pasador.x + math.cos(angulo) * (pasador.radio + pelota.radio + 20)
            pelota.y = pasador.y + math.sin(angulo) * (pasador.radio + pelota.radio + 20)

        pelota.pegada = False
        pelota.dueno = None
        pasador.tiene_balon = False
        return True
    else:
        # Pase fallido: 0.00075 - 0.002 px/s
        angulo = random.uniform(0, 2 * math.pi)
        velocidad = random.uniform(15, 40) / 200.0
        pelota.vx = math.cos(angulo) * velocidad
        pelota.vy = math.sin(angulo) * velocidad
        pelota.x = pasador.x + math.cos(angulo) * (pasador.radio + pelota.radio + 10)
        pelota.y = pasador.y + math.sin(angulo) * (pasador.radio + pelota.radio + 10)
        pelota.pegada = False
        pelota.dueno = None
        pasador.tiene_balon = False
        return False


def ejecutar_pase_por_direccion(pasador, dx, dy, pelota, equipos, es_largo=False, solo_companeros=True):
    """
    Busca el receptor más cercano en la dirección indicada (60 grados).
    Solo pasa a compañeros si solo_companeros=True (siempre debe ser True).
    """
    equipo_pasador = None
    for eq in equipos:
        if pasador in eq.jugadores:
            equipo_pasador = eq
            break
    if equipo_pasador is None:
        return False

    angulo_dir = math.atan2(dy, dx)
    mejor = None
    mejor_dist = float('inf')
    for comp in equipo_pasador.jugadores:
        if comp == pasador or comp.tiene_balon:
            continue
        dxc = comp.x - pasador.x
        dyc = comp.y - pasador.y
        if dxc == 0 and dyc == 0:
            continue
        angulo_comp = math.atan2(dyc, dxc)
        diff = abs(angulo_dir - angulo_comp)
        if diff > math.pi:
            diff = 2 * math.pi - diff
        if diff < math.pi / 3:  # 60 grados
            dist = math.hypot(dxc, dyc)
            if dist < mejor_dist:
                mejor_dist = dist
                mejor = comp

    if mejor is not None:
        return ejecutar_pase(pasador, mejor, pelota, es_largo)
    else:
        if solo_companeros:
            return False
        else:
            return ejecutar_pase(pasador, None, pelota, es_largo)


# ------------------------------------------------------------
#  Funciones de recepción
# ------------------------------------------------------------
def intentar_recibir(receptor, pelota):
    if pelota.pegada:
        return False
    if receptor.tiene_balon:
        return False

    dist = distancia_objetos(receptor, pelota)
    if dist > receptor.radio + pelota.radio + 5:
        return False

    if hasattr(receptor, 'stats'):
        prob = 0.5 + 0.5 * (receptor.stats.pase / 100.0)
        prob *= (1.0 - receptor.stats.fatiga / 200.0)
    else:
        prob = 0.7

    if random.random() < prob:
        receptor.recoger_balon(pelota)
        return True
    else:
        # Rebote: 0.00075 - 0.00175 px/s
        angulo = random.uniform(0, 2 * math.pi)
        velocidad = random.uniform(15, 35) / 200.0
        pelota.vx = math.cos(angulo) * velocidad
        pelota.vy = math.sin(angulo) * velocidad
        pelota.pegada = False
        pelota.dueno = None
        return False


# ------------------------------------------------------------
#  Funciones de tiro
# ------------------------------------------------------------
def calcular_precision_tiro(tirador, distancia_porteria, angulo_porteria):
    if not hasattr(tirador, 'stats'):
        return 0.5
    stat_tiro = tirador.stats.tiro / 100.0
    factor_fatiga = 1.0 - (tirador.stats.fatiga / 200.0)
    factor_distancia = 1.0 - min(1.0, distancia_porteria / 700.0)
    factor_angulo = 1.0 - abs(angulo_porteria) / (math.pi / 2)
    precision = (0.2 + 0.8 * stat_tiro) * factor_fatiga * factor_distancia * factor_angulo
    return max(0.1, min(0.95, precision))


def ejecutar_tiro(tirador, pelota):
    if tirador.equipo == "Local":
        porteria_x = SCREEN_WIDTH
    else:
        porteria_x = 0
    porteria_y = SCREEN_HEIGHT / 2

    dist = distancia_objetos(tirador, type('obj', (object,), {'x': porteria_x, 'y': porteria_y})())
    angulo = math.atan2(porteria_y - tirador.y, porteria_x - tirador.x)

    precision = calcular_precision_tiro(tirador, dist, angulo)
    exito = random.random() < precision

    if hasattr(tirador, 'stats'):
        tirador.stats.registrar_tiro(exito)

    # Tiro: 0.0075 - 0.015 px/s
    potencia = (150 + 150 * (tirador.stats.tiro / 100.0 if hasattr(tirador, 'stats') else 0.5)) / 200.0
    potencia *= (1.0 - tirador.stats.fatiga / 300.0 if hasattr(tirador, 'stats') else 1.0)

    if exito:
        desviacion = random.uniform(-0.05, 0.05)
        angulo_final = angulo + desviacion
        pelota.vx = math.cos(angulo_final) * potencia
        pelota.vy = math.sin(angulo_final) * potencia
    else:
        desviacion = random.uniform(-0.5, 0.5)
        angulo_final = angulo + desviacion
        pelota.vx = math.cos(angulo_final) * potencia * random.uniform(0.5, 1.0)
        pelota.vy = math.sin(angulo_final) * potencia * random.uniform(0.5, 1.0)

    pelota.pegada = False
    pelota.dueno = None
    tirador.tiene_balon = False
    aplicar_limites_campo(pelota)
    return exito


# ------------------------------------------------------------
#  Funciones de conducción
# ------------------------------------------------------------
def aplicar_conduccion(jugador, pelota, dt):
    if not pelota.pegada or pelota.dueno != jugador:
        return

    velocidad = math.hypot(jugador.vx, jugador.vy)
    if velocidad < 10:
        pelota.x = jugador.x
        pelota.y = jugador.y - jugador.radio - pelota.radio - 4
        return

    dx = jugador.vx / velocidad
    dy = jugador.vy / velocidad

    # Conducción extremadamente corta (no se modifica por la velocidad)
    distancia = 2 + velocidad * 0.005
    variacion = random.uniform(-1, 1)
    pelota.x = jugador.x + dx * (distancia + variacion)
    pelota.y = jugador.y + dy * (distancia + variacion)

    aplicar_limites_campo(pelota)


def puede_conducir(jugador):
    if not hasattr(jugador, 'stats'):
        return True
    if jugador.stats.fatiga > 80:
        return random.random() < 0.5
    if jugador.stats.regate < 30:
        return random.random() < 0.7
    return True


# ------------------------------------------------------------
#  Funciones de intercepción y línea de pase
# ------------------------------------------------------------
def distancia_a_segmento(px, py, x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def hay_linea_pase(jug1, jug2, equipo_rival, radio_deteccion=50):
    """
    Verifica que no haya rivales en la línea entre jug1 y jug2.
    Retorna True si hay línea de pase libre.
    """
    for rival in equipo_rival.jugadores:
        if distancia_a_segmento(rival.x, rival.y, jug1.x, jug1.y, jug2.x, jug2.y) < radio_deteccion:
            return False
    return True


def puede_interceptar_pase(defensor, pelota, pasador, receptor):
    x1, y1 = pasador.x, pasador.y
    x2, y2 = receptor.x, receptor.y
    dist_linea = distancia_a_segmento(defensor.x, defensor.y, x1, y1, x2, y2)
    if dist_linea < 50:
        dist_pelota = distancia_objetos(defensor, pelota)
        if dist_pelota < 150:
            if hasattr(defensor, 'stats'):
                prob = 0.3 + 0.7 * (defensor.stats.robo / 100.0)
                prob *= (1.0 - defensor.stats.fatiga / 200.0)
            else:
                prob = 0.5
            return random.random() < prob
    return False


# ------------------------------------------------------------
#  Funciones adicionales para pase por proximidad
# ------------------------------------------------------------
def encontrar_companero_mas_cercano(pasador, companeros, equipo_rival, radio_max=500):
    """
    Encuentra el compañero más cercano que tenga línea de pase libre.
    Retorna el jugador o None.
    """
    mejor = None
    mejor_dist = float('inf')
    for comp in companeros:
        if comp == pasador or comp.tiene_balon:
            continue
        # Verificar línea de pase libre
        if not hay_linea_pase(pasador, comp, equipo_rival, radio_deteccion=40):
            continue
        dist = distancia_objetos(pasador, comp)
        if dist < mejor_dist and dist < radio_max:
            mejor_dist = dist
            mejor = comp
    return mejor


# ------------------------------------------------------------
#  Fin del módulo
# ------------------------------------------------------------