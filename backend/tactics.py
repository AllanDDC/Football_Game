# backend/tactics.py
"""
Módulo de tácticas y estilos de juego para equipos de fútbol.
Define parámetros de comportamiento colectivo y funciones para
aplicarlos a la IA de los jugadores.
Incluye parámetros para controlar la altura de los delanteros en defensa.
"""

import random
import math
from .config import PLAYER_SPEED, AI_CHASE_DISTANCE, SCREEN_WIDTH, SCREEN_HEIGHT
from .physics import mover_hacia, distancia_objetos


# ------------------------------------------------------------
#  Definición de tácticas (diccionarios con parámetros)
# ------------------------------------------------------------
class Tactica:
    """
    Representa un estilo de juego con parámetros ajustables.
    Los parámetros influyen en el comportamiento de la IA de todo el equipo.
    """

    def __init__(self, nombre, params):
        self.nombre = nombre
        self.params = params

    def __str__(self):
        return f"Táctica: {self.nombre}"

    def obtener_param(self, key, default=None):
        return self.params.get(key, default)


# Diccionario con las tácticas predefinidas
TACTICAS = {
    # Tiki-taka: posesión, pases cortos, presión tras pérdida
    "tiki_taka": Tactica("Tiki-taka", {
        "posesion": 0.9,            # 0-1, prioridad de mantener la pelota
        "pase_largo": 0.1,          # 0-1, tendencia a pases largos
        "presion_alta": 0.8,        # 0-1, intensidad de presión tras pérdida
        "velocidad_ataque": 0.4,    # 0-1, velocidad de transición ofensiva
        "profundidad_defensiva": 0.3, # 0-1, línea defensiva alta (0) o baja (1)
        "altura_delanteros_defensiva": 0.2, # 0-1, delanteros se quedan arriba (0) o bajan (1)
        "regate_frecuencia": 0.6,   # 0-1, frecuencia de regates
        "distancia_presion": 150,   # distancia a la que presionar al poseedor
        "ancho": 0.6,               # 0-1, amplitud del equipo
    }),
    # Catenaccio: defensivo, contraataque
    "catenaccio": Tactica("Catenaccio", {
        "posesion": 0.3,
        "pase_largo": 0.8,
        "presion_alta": 0.1,
        "velocidad_ataque": 0.9,
        "profundidad_defensiva": 0.9,
        "altura_delanteros_defensiva": 0.8,  # delanteros bajan mucho
        "regate_frecuencia": 0.2,
        "distancia_presion": 80,
        "ancho": 0.3,
    }),
    # Presión alta: agresivo, recuperación rápida
    "presion_alta": Tactica("Presión alta", {
        "posesion": 0.5,
        "pase_largo": 0.3,
        "presion_alta": 0.95,
        "velocidad_ataque": 0.7,
        "profundidad_defensiva": 0.1,
        "altura_delanteros_defensiva": 0.1,  # delanteros siempre arriba
        "regate_frecuencia": 0.5,
        "distancia_presion": 250,
        "ancho": 0.5,
    }),
    # Fútbol total: dinámico, todos atacan y defienden
    "total": Tactica("Fútbol total", {
        "posesion": 0.6,
        "pase_largo": 0.4,
        "presion_alta": 0.7,
        "velocidad_ataque": 0.7,
        "profundidad_defensiva": 0.4,
        "altura_delanteros_defensiva": 0.4,
        "regate_frecuencia": 0.7,
        "distancia_presion": 200,
        "ancho": 0.7,
    }),
    # Jogo bonito: ofensivo, regate, toque
    "jogo_bonito": Tactica("Jogo bonito", {
        "posesion": 0.8,
        "pase_largo": 0.2,
        "presion_alta": 0.4,
        "velocidad_ataque": 0.5,
        "profundidad_defensiva": 0.2,
        "altura_delanteros_defensiva": 0.2,
        "regate_frecuencia": 0.9,
        "distancia_presion": 120,
        "ancho": 0.8,
    }),
    # Contragolpe: defensivo y letal al contraatacar
    "contragolpe": Tactica("Contragolpe", {
        "posesion": 0.2,
        "pase_largo": 0.9,
        "presion_alta": 0.2,
        "velocidad_ataque": 1.0,
        "profundidad_defensiva": 0.8,
        "altura_delanteros_defensiva": 0.6,
        "regate_frecuencia": 0.3,
        "distancia_presion": 60,
        "ancho": 0.2,
    }),
    # Bloque bajo: ultradefensivo, agrupa jugadores cerca del área
    "bloque_bajo": Tactica("Bloque bajo", {
        "posesion": 0.1,
        "pase_largo": 0.9,
        "presion_alta": 0.0,
        "velocidad_ataque": 0.2,
        "profundidad_defensiva": 1.0,
        "altura_delanteros_defensiva": 1.0,  # delanteros bajan al máximo
        "regate_frecuencia": 0.1,
        "distancia_presion": 40,
        "ancho": 0.1,
    }),
}


# ------------------------------------------------------------
#  Funciones de selección de táctica
# ------------------------------------------------------------
def seleccionar_tactica_por_marcador(goles_favor, goles_contra, tiempo_restante, minuto_total=90):
    """
    Selecciona una táctica según el marcador y el tiempo restante.
    """
    diferencia = goles_favor - goles_contra
    if minuto_total <= 0:
        tiempo_norm = 1.0
    else:
        tiempo_norm = tiempo_restante / minuto_total

    if diferencia > 0 and tiempo_norm < 0.3:
        return random.choice(["catenaccio", "bloque_bajo", "catenaccio"])
    elif diferencia > 0 and tiempo_norm < 0.6:
        return random.choice(["tiki_taka", "catenaccio"])
    elif diferencia < 0:
        if tiempo_norm < 0.3:
            return "presion_alta"
        return random.choice(["total", "jogo_bonito", "presion_alta"])
    else:
        return random.choice(["tiki_taka", "total", "presion_alta"])


# ------------------------------------------------------------
#  Aplicación de táctica a un equipo
# ------------------------------------------------------------
def aplicar_tactica_a_equipo(equipo, tactica_nombre, pelota, dt):
    """
    Asigna los parámetros tácticos al equipo para que la IA los use.
    """
    tactica = TACTICAS.get(tactica_nombre)
    if tactica is None:
        return

    params = tactica.params
    # Guardar todos los parámetros en el equipo para que la IA los lea
    equipo.tactica_actual = tactica_nombre
    equipo.distancia_presion = params.get("distancia_presion", AI_CHASE_DISTANCE)
    equipo.profundidad_defensiva = params.get("profundidad_defensiva", 0.5)
    equipo.altura_delanteros_defensiva = params.get("altura_delanteros_defensiva", 0.5)
    equipo.ancho = params.get("ancho", 0.5)
    equipo.velocidad_ataque = params.get("velocidad_ataque", 0.5)
    equipo.presion_alta = params.get("presion_alta", 0.5)
    equipo.regate_frecuencia = params.get("regate_frecuencia", 0.5)
    equipo.pase_largo = params.get("pase_largo", 0.5)


# ------------------------------------------------------------
#  Funciones de ayuda para la IA (para ser usadas desde ai.py)
# ------------------------------------------------------------
def obtener_distancia_presion(equipo):
    return getattr(equipo, 'distancia_presion', AI_CHASE_DISTANCE)

def obtener_factor_posesion(equipo):
    tactica_nombre = getattr(equipo, 'tactica_actual', 'tiki_taka')
    tactica = TACTICAS.get(tactica_nombre)
    return tactica.params.get("posesion", 0.5) if tactica else 0.5

def obtener_factor_pase_largo(equipo):
    tactica_nombre = getattr(equipo, 'tactica_actual', 'tiki_taka')
    tactica = TACTICAS.get(tactica_nombre)
    return tactica.params.get("pase_largo", 0.5) if tactica else 0.5

def obtener_frecuencia_regate(equipo):
    tactica_nombre = getattr(equipo, 'tactica_actual', 'tiki_taka')
    tactica = TACTICAS.get(tactica_nombre)
    return tactica.params.get("regate_frecuencia", 0.5) if tactica else 0.5

def obtener_profundidad_defensiva(equipo):
    return getattr(equipo, 'profundidad_defensiva', 0.5)

def obtener_altura_delanteros_defensiva(equipo):
    """0 = delanteros arriba, 1 = delanteros abajo (defensivo)"""
    return getattr(equipo, 'altura_delanteros_defensiva', 0.5)


# ------------------------------------------------------------
#  Lógica de cambios de táctica durante el partido
# ------------------------------------------------------------
def actualizar_tactica_segun_marcador(equipo, goles_favor, goles_contra, tiempo_restante, minuto_total=90):
    """
    Cambia la táctica del equipo según el marcador y el tiempo.
    Se llama desde game.py cada cierto tiempo.
    """
    tactica_nombre = seleccionar_tactica_por_marcador(goles_favor, goles_contra, tiempo_restante, minuto_total)
    if tactica_nombre != getattr(equipo, 'tactica_actual', None):
        aplicar_tactica_a_equipo(equipo, tactica_nombre, None, 0)
        # El mensaje de cambio se puede mostrar o no (silenciado para evitar spam)
        # print(f"El equipo {equipo.nombre} cambia a táctica: {tactica_nombre}")
        return True
    return False


# ------------------------------------------------------------
#  Funciones para generar formaciones según táctica
# ------------------------------------------------------------
def obtener_formacion_para_tactica(tactica_nombre):
    """
    Devuelve una lista de posiciones base (x, y) en proporción (0-1)
    para una formación típica de la táctica dada.
    """
    from .ai import FORMACION_LOCAL, FORMACION_RIVAL
    if tactica_nombre in ["catenaccio", "bloque_bajo"]:
        formacion = [(0.85, 0.5), (0.7, 0.2), (0.7, 0.35), (0.7, 0.65), (0.7, 0.8),
                     (0.55, 0.2), (0.55, 0.4), (0.55, 0.6), (0.55, 0.8),
                     (0.4, 0.3), (0.4, 0.7)]
    elif tactica_nombre in ["presion_alta", "total"]:
        formacion = [(0.9, 0.5), (0.8, 0.15), (0.8, 0.35), (0.8, 0.65), (0.8, 0.85),
                     (0.6, 0.15), (0.6, 0.4), (0.6, 0.6), (0.6, 0.85),
                     (0.4, 0.25), (0.4, 0.75)]
    else:
        formacion = FORMACION_LOCAL
    return formacion