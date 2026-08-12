# backend/dribbling.py
"""
Módulo especializado en la mecánica de regate y conducción de balón.
Gestiona:
- Cálculo de probabilidades de éxito en regates (1vs1).
- Ejecución de regates con efectos en la pelota y los jugadores.
- Sistema de "radio opaco" para pases largos (zona de no interceptación).
- Actualización de estadísticas tras acciones de regate.
"""

import math
import random
from .config import PLAYER_RADIUS, BALL_RADIUS, SCREEN_WIDTH, SCREEN_HEIGHT
from .physics import distancia_objetos, mover_hacia, aplicar_limites_campo
from .player_stats import PlayerStats


# ------------------------------------------------------------
#  Cálculo de probabilidades de regate
# ------------------------------------------------------------
def calcular_probabilidad_regate(atacante, defensor):
    """
    Calcula la probabilidad de que el atacante supere al defensor en un 1vs1.
    Usa estadísticas de regate (atacante) y robo (defensor), así como fatiga.

    :param atacante: Jugador que ataca (con atributo .stats)
    :param defensor: Jugador que defiende (con atributo .stats)
    :return: Probabilidad entre 0.0 y 1.0
    """
    if not hasattr(atacante, 'stats') or not hasattr(defensor, 'stats'):
        # Si faltan estadísticas, usar azar puro
        return 0.5

    stat_regate = atacante.stats.regate / 100.0  # 0-1
    stat_robo = defensor.stats.robo / 100.0      # 0-1

    # Probabilidad base: regate / (regate + robo)
    if stat_regate + stat_robo == 0:
        prob = 0.5
    else:
        prob = stat_regate / (stat_regate + stat_robo)

    # Factor de cansancio del atacante (penaliza)
    factor_fatiga_atacante = 1.0 - (atacante.stats.fatiga / 200.0)  # hasta 50% de reducción
    # Factor de cansancio del defensor (favorece al atacante si el defensor está cansado)
    factor_fatiga_defensor = 1.0 + (defensor.stats.fatiga / 200.0)  # hasta +50%

    prob *= factor_fatiga_atacante
    prob *= factor_fatiga_defensor

    # Limitar entre 0.1 y 0.9 para dar siempre algo de azar
    return max(0.1, min(0.9, prob))


def calcular_probabilidad_robo(defensor, atacante):
    """
    Probabilidad de que el defensor robe el balón al atacante.
    Es la inversa de la probabilidad de regate del atacante.
    """
    return 1.0 - calcular_probabilidad_regate(atacante, defensor)


# ------------------------------------------------------------
#  Ejecución de regate
# ------------------------------------------------------------
def ejecutar_regate(atacante, defensor, pelota):
    """
    Intenta ejecutar un regate entre atacante y defensor.
    Actualiza estadísticas y la posición de la pelota según el resultado.

    :param atacante: Jugador con la pelota
    :param defensor: Jugador rival que intenta robar
    :param pelota: Objeto Pelota
    :return: True si el regate tiene éxito (el atacante supera al defensor), False si falla
    """
    # Calcular probabilidad de éxito
    prob = calcular_probabilidad_regate(atacante, defensor)
    exito = random.random() < prob

    if exito:
        # Regate exitoso: el atacante se mueve más allá del defensor
        # Registrar estadísticas
        if hasattr(atacante, 'stats'):
            atacante.stats.registrar_regate(True)
        if hasattr(defensor, 'stats'):
            defensor.stats.registrar_robo()  # aunque falló, lo registramos como intento de robo
        # La pelota se adelanta en la dirección de movimiento del atacante
        _avanzar_pelota_despues_regate(atacante, defensor, pelota, exito=True)
    else:
        # Regate fallido: el defensor roba la pelota
        if hasattr(atacante, 'stats'):
            atacante.stats.registrar_regate(False)
        if hasattr(defensor, 'stats'):
            defensor.stats.registrar_robo()
        # La pelota se suelta y sale despedida
        _avanzar_pelota_despues_regate(atacante, defensor, pelota, exito=False)

    return exito


def _avanzar_pelota_despues_regate(atacante, defensor, pelota, exito):
    """
    Ajusta la posición y velocidad de la pelota tras un regate.
    Si el regate es exitoso, la pelota avanza delante del atacante.
    Si falla, la pelota se desvía hacia el defensor.
    """
    if exito:
        # La pelota se adelanta en la dirección del movimiento del atacante
        velocidad = math.hypot(atacante.vx, atacante.vy)
        if velocidad > 10:
            dx = atacante.vx / velocidad
            dy = atacante.vy / velocidad
        else:
            # Si está quieto, hacia adelante (arriba)
            dx, dy = 0, -1

        # Colocar la pelota unos 30 píxeles delante del atacante
        pelota.x = atacante.x + dx * (atacante.radio + pelota.radio + 30)
        pelota.y = atacante.y + dy * (atacante.radio + pelota.radio + 30)
        pelota.pegada = False
        pelota.dueno = None
        atacante.tiene_balon = False
        # Dar un pequeño impulso a la pelota
        pelota.vx = dx * 100
        pelota.vy = dy * 100
    else:
        # Regate fallido: la pelota se desvía aleatoriamente
        angulo = random.uniform(0, 2 * math.pi)
        velocidad = random.uniform(50, 200)
        pelota.x = defensor.x + math.cos(angulo) * (defensor.radio + pelota.radio + 10)
        pelota.y = defensor.y + math.sin(angulo) * (defensor.radio + pelota.radio + 10)
        pelota.pegada = False
        pelota.dueno = None
        atacante.tiene_balon = False
        pelota.vx = math.cos(angulo) * velocidad
        pelota.vy = math.sin(angulo) * velocidad

    # Asegurar que la pelota no salga del campo
    aplicar_limites_campo(pelota)


# ------------------------------------------------------------
#  Radio opaco para pases largos (área de no interceptación)
# ------------------------------------------------------------
def obtener_radio_pase_largo(tirador, potencia=1.0):
    """
    Calcula el radio del área opaca alrededor del tirador para pases largos.
    El radio depende de la potencia del pase y de la estadística de pase del jugador.

    :param tirador: Jugador que realiza el pase
    :param potencia: Factor de potencia (0.5-1.5), por defecto 1.0
    :return: Radio en píxeles
    """
    if not hasattr(tirador, 'stats'):
        return 150  # valor por defecto

    stat_pase = tirador.stats.pase / 100.0  # 0-1
    # El radio base es 100 + 100 * stat_pase * potencia
    radio_base = 100 + 100 * stat_pase * potencia
    # Limitar entre 80 y 300
    return max(80, min(300, radio_base))


def esta_dentro_radio_opaco(pelota, centro, radio):
    """
    Verifica si la pelota está dentro del radio opaco alrededor del centro.
    Esto determina si un pase largo puede ser interceptado.
    """
    return distancia_objetos(pelota, centro) < radio


# ------------------------------------------------------------
#  Funciones para regate en conducción (cuando el jugador corre)
# ------------------------------------------------------------
def aplicar_regate_conduccion(jugador, pelota, dt):
    """
    Durante la conducción, el jugador puede realizar pequeños toques de regate
    para mantener el control. Esto modifica la posición de la pelota
    para que se adelante ligeramente y no se pegue al pie.
    """
    if not pelota.pegada or pelota.dueno != jugador:
        return

    velocidad = math.hypot(jugador.vx, jugador.vy)
    if velocidad < 10:
        return

    # Dirección de movimiento
    dx = jugador.vx / velocidad
    dy = jugador.vy / velocidad

    # Distancia de conducción: mayor velocidad = mayor distancia
    distancia = 10 + velocidad * 0.03

    # Pequeña variación aleatoria para simular toques imprecisos
    variacion = random.uniform(-5, 5)
    pelota.x = jugador.x + dx * (distancia + variacion)
    pelota.y = jugador.y + dy * (distancia + variacion)

    # Limitar dentro del campo
    aplicar_limites_campo(pelota)


# ------------------------------------------------------------
#  Simulación de tiro (pase largo o disparo)
# ------------------------------------------------------------
def realizar_tiro(jugador, pelota, potencia, precision):
    """
    Ejecuta un tiro o pase largo.
    La precisión y potencia se ven afectadas por las estadísticas y fatiga.
    Retorna (exito, angulo, velocidad) donde éxito indica si el tiro va a puerta.
    """
    if not hasattr(jugador, 'stats'):
        # Valores por defecto si no hay estadísticas
        stat_tiro = 0.5
        fatiga_factor = 1.0
    else:
        stat_tiro = jugador.stats.tiro / 100.0
        fatiga_factor = 1.0 - (jugador.stats.fatiga / 200.0)

    # La precisión real es la estadística ajustada por fatiga
    precision_real = precision * stat_tiro * fatiga_factor
    # La potencia real es la estadística ajustada por fatiga
    potencia_real = potencia * (0.8 + 0.2 * stat_tiro) * fatiga_factor

    # Determinar si el tiro va a puerta (para disparos)
    exito = random.random() < precision_real

    # Ángulo de desviación (si falla, mayor desviación)
    if exito:
        desviacion = random.uniform(-0.05, 0.05)  # muy precisa
    else:
        desviacion = random.uniform(-0.3, 0.3)  # desviación considerable

    # Velocidad resultante
    velocidad = 200 + 400 * potencia_real

    return exito, desviacion, velocidad


# ------------------------------------------------------------
#  Clase opcional para manejar el estado de regate (para IA)
# ------------------------------------------------------------
class DribblingState:
    """
    Almacena el estado del regate para un jugador (útil para la IA).
    """
    def __init__(self):
        self.ultimo_regate = 0.0
        self.cooldown = 0.5  # segundos entre regates
        self.regates_intentados = 0
        self.regates_exitosos = 0

    def puede_regatear(self, tiempo_actual):
        return (tiempo_actual - self.ultimo_regate) >= self.cooldown

    def registrar_intento(self, exitoso):
        self.ultimo_regate = 0.0  # se actualizará con el tiempo desde fuera
        self.regates_intentados += 1
        if exitoso:
            self.regates_exitosos += 1


# ------------------------------------------------------------
#  Fin del módulo
# ------------------------------------------------------------