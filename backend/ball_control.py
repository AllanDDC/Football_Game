# backend/ball_control.py
"""
Módulo especializado en el control del balón:
- Pases (cortos y largos) con dirección controlada por teclado
- Tiros a portería
- Conducción y recepción
- Verificación de línea de pase (para Ctrl+Z)
- Intercepciones de pases
- Interacción con estadísticas, fatiga y tácticas
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
    """
    Calcula la precisión de un pase según estadísticas del pasador,
    distancia y tipo de pase.

    :param pasador: Jugador que realiza el pase
    :param distancia: Distancia en píxeles
    :param es_pase_largo: True si es pase largo (afecta precisión)
    :return: Probabilidad de éxito (0.0-1.0)
    """
    if not hasattr(pasador, 'stats'):
        return 0.7  # valor por defecto

    stat_pase = pasador.stats.pase / 100.0  # 0-1
    # La distancia máxima efectiva es 600 píxeles
    factor_distancia = 1.0 - min(1.0, distancia / 600.0)
    factor_fatiga = 1.0 - (pasador.stats.fatiga / 200.0)

    # Los pases largos son menos precisos si la estadística es baja
    if es_pase_largo:
        factor_largo = 0.8 + 0.2 * stat_pase
    else:
        factor_largo = 1.0

    precision = (0.3 + 0.7 * stat_pase) * factor_distancia * factor_fatiga * factor_largo
    return max(0.1, min(0.95, precision))


def ejecutar_pase(pasador, receptor, pelota, es_largo=False):
    """
    Ejecuta un pase entre dos jugadores.
    Actualiza estadísticas y la posición/velocidad de la pelota.

    :param pasador: Jugador que pasa
    :param receptor: Jugador que recibe (puede ser None para pase al espacio)
    :param pelota: Objeto Pelota
    :param es_largo: Si es pase largo (True) o corto (False)
    :return: True si el pase es exitoso, False si falla
    """
    # Calcular distancia
    if receptor:
        distancia = distancia_objetos(pasador, receptor)
    else:
        distancia = random.uniform(100, 300)  # pase al espacio

    # Calcular precisión
    precision = calcular_precision_pase(pasador, distancia, es_largo)
    exito = random.random() < precision

    # Registrar estadísticas
    if hasattr(pasador, 'stats'):
        pasador.stats.registrar_pase(exito)

    if exito:
        if receptor:
            velocidad_base = 200 + 100 * (1 - precision)
            if es_largo:
                velocidad_base *= 1.5  # más rápido en pases largos
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

            # Para pases largos, la pelota va más alta (simulación en 2D: efecto de arco)
            if es_largo:
                pelota.vy -= 50  # un poco más arriba
        else:
            # Pase al espacio: dirección aleatoria
            angulo = random.uniform(0, 2 * math.pi)
            velocidad = 150 + random.uniform(0, 100)
            pelota.vx = math.cos(angulo) * velocidad
            pelota.vy = math.sin(angulo) * velocidad
            pelota.x = pasador.x + math.cos(angulo) * (pasador.radio + pelota.radio + 20)
            pelota.y = pasador.y + math.sin(angulo) * (pasador.radio + pelota.radio + 20)

        # La pelota deja de estar pegada
        pelota.pegada = False
        pelota.dueno = None
        pasador.tiene_balon = False
        return True
    else:
        # Pase fallido: la pelota se pierde
        angulo = random.uniform(0, 2 * math.pi)
        velocidad = random.uniform(50, 150)
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
    Busca el receptor más cercano en la dirección indicada (dx, dy normalizados)
    y ejecuta un pase hacia él. Si no hay receptor en un ángulo de 60 grados,
    y solo_companeros es True, no hace nada. Si es False, hace un pase al espacio.

    :param pasador: Jugador que pasa
    :param dx, dy: Vector de dirección normalizado (de las teclas de movimiento)
    :param pelota: Objeto Pelota
    :param equipos: Lista de equipos [equipo_local, equipo_rival] para buscar al compañero
    :param es_largo: True para pase largo (Shift+Espacio)
    :param solo_companeros: Si es True, solo pasa si hay un compañero en la dirección; si False, pase al espacio
    :return: True si se ejecutó un pase, False si falló o no había receptor
    """
    # Obtener el equipo del pasador
    equipo_pasador = None
    for eq in equipos:
        if pasador in eq.jugadores:
            equipo_pasador = eq
            break
    if equipo_pasador is None:
        return False

    # Buscar el mejor receptor en la dirección
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
        # Si solo_companeros es True, no ejecutar pase al espacio
        if solo_companeros:
            return False
        else:
            return ejecutar_pase(pasador, None, pelota, es_largo)


# ------------------------------------------------------------
#  Funciones de recepción
# ------------------------------------------------------------
def intentar_recibir(receptor, pelota):
    """
    Un jugador intenta recibir la pelota si está cerca.
    La probabilidad de éxito depende de la estadística de pase (recepción).
    """
    if pelota.pegada:
        return False
    if receptor.tiene_balon:
        return False

    dist = distancia_objetos(receptor, pelota)
    if dist > receptor.radio + pelota.radio + 5:
        return False

    # Probabilidad de recepción: basada en estadística de pase
    if hasattr(receptor, 'stats'):
        prob = 0.5 + 0.5 * (receptor.stats.pase / 100.0)
        prob *= (1.0 - receptor.stats.fatiga / 200.0)
    else:
        prob = 0.7

    if random.random() < prob:
        # Recepción exitosa
        receptor.recoger_balon(pelota)
        return True
    else:
        # Recepción fallida: la pelota rebota
        angulo = random.uniform(0, 2 * math.pi)
        velocidad = random.uniform(30, 80)
        pelota.vx = math.cos(angulo) * velocidad
        pelota.vy = math.sin(angulo) * velocidad
        pelota.pegada = False
        pelota.dueno = None
        return False


# ------------------------------------------------------------
#  Funciones de tiro
# ------------------------------------------------------------
def calcular_precision_tiro(tirador, distancia_porteria, angulo_porteria):
    """
    Calcula la precisión de un tiro a portería.
    """
    if not hasattr(tirador, 'stats'):
        return 0.5

    stat_tiro = tirador.stats.tiro / 100.0
    factor_fatiga = 1.0 - (tirador.stats.fatiga / 200.0)
    factor_distancia = 1.0 - min(1.0, distancia_porteria / 700.0)
    factor_angulo = 1.0 - abs(angulo_porteria) / (math.pi / 2)

    precision = (0.2 + 0.8 * stat_tiro) * factor_fatiga * factor_distancia * factor_angulo
    return max(0.1, min(0.95, precision))


def ejecutar_tiro(tirador, pelota):
    """
    Ejecuta un tiro a portería.
    El tiro se dirige a la portería rival.
    """
    # Determinar portería rival según equipo del tirador
    if tirador.equipo == "Local":
        porteria_x = SCREEN_WIDTH
    else:
        porteria_x = 0
    porteria_y = SCREEN_HEIGHT / 2

    # Calcular distancia y ángulo a la portería
    dist = distancia_objetos(tirador, type('obj', (object,), {'x': porteria_x, 'y': porteria_y})())
    angulo = math.atan2(porteria_y - tirador.y, porteria_x - tirador.x)

    # Calcular precisión
    precision = calcular_precision_tiro(tirador, dist, angulo)
    exito = random.random() < precision

    # Registrar estadísticas
    if hasattr(tirador, 'stats'):
        tirador.stats.registrar_tiro(exito)

    # Potencia del tiro
    potencia = 300 + 300 * (tirador.stats.tiro / 100.0 if hasattr(tirador, 'stats') else 0.5)
    potencia *= (1.0 - tirador.stats.fatiga / 300.0 if hasattr(tirador, 'stats') else 1.0)

    # Dirección del tiro
    if exito:
        # Tiro a puerta: con pequeña desviación aleatoria
        desviacion = random.uniform(-0.05, 0.05)
        angulo_final = angulo + desviacion
        pelota.vx = math.cos(angulo_final) * potencia
        pelota.vy = math.sin(angulo_final) * potencia
    else:
        # Tiro fallido: desviación grande
        desviacion = random.uniform(-0.5, 0.5)
        angulo_final = angulo + desviacion
        pelota.vx = math.cos(angulo_final) * potencia * random.uniform(0.5, 1.0)
        pelota.vy = math.sin(angulo_final) * potencia * random.uniform(0.5, 1.0)

    # Soltar la pelota
    pelota.pegada = False
    pelota.dueno = None
    tirador.tiene_balon = False
    aplicar_limites_campo(pelota)
    return exito


# ------------------------------------------------------------
#  Funciones de conducción
# ------------------------------------------------------------
def aplicar_conduccion(jugador, pelota, dt):
    """
    Maneja la conducción del balón mientras el jugador corre.
    La pelota se adelanta en la dirección de movimiento.
    """
    if not pelota.pegada or pelota.dueno != jugador:
        return

    velocidad = math.hypot(jugador.vx, jugador.vy)
    if velocidad < 10:
        # Si está quieto, la pelota se coloca justo delante
        pelota.x = jugador.x
        pelota.y = jugador.y - jugador.radio - pelota.radio - 4
        return

    # Dirección de movimiento
    dx = jugador.vx / velocidad
    dy = jugador.vy / velocidad

    # Distancia de conducción: mayor velocidad = más adelante
    distancia = 10 + velocidad * 0.03
    variacion = random.uniform(-3, 3)
    pelota.x = jugador.x + dx * (distancia + variacion)
    pelota.y = jugador.y + dy * (distancia + variacion)

    # Limitar dentro del campo
    aplicar_limites_campo(pelota)


def puede_conducir(jugador):
    """
    Verifica si un jugador puede conducir el balón.
    Depende de la estadística de regate y fatiga.
    """
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
    """Distancia desde un punto (px, py) al segmento (x1,y1)-(x2,y2)."""
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
    """
    Determina si un defensor puede interceptar un pase.
    Se basa en la posición del defensor respecto a la línea de pase.
    """
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
#  Fin del módulo
# ------------------------------------------------------------