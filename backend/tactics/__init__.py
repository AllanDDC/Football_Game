# backend/tactics/__init__.py
"""
Módulo de tácticas (punto de entrada único).
Exporta todas las clases de táctica, funciones de compatibilidad y utilidades.
"""

import random
from .base import TacticaBase, _posicion_base, _get_velocidad_efectiva
from .catenaccio import Catenaccio
from .tiki_taka import TikiTaka
from .presion_alta import PresionAlta
from .contragolpe import Contragolpe
from .total import Total
from .jogo_bonito import JogoBonito
from .bloque_bajo import BloqueBajo

# ------------------------------------------------------------
#  Registro de clases de táctica
# ------------------------------------------------------------
TACTICAS_CLASES = {
    "catenaccio": Catenaccio,
    "tiki_taka": TikiTaka,
    "presion_alta": PresionAlta,
    "contragolpe": Contragolpe,
    "total": Total,
    "jogo_bonito": JogoBonito,
    "bloque_bajo": BloqueBajo,
}

# ------------------------------------------------------------
#  Instancias de tácticas (para compatibilidad con código antiguo)
# ------------------------------------------------------------
TACTICAS = {
    "catenaccio": Catenaccio(),
    "tiki_taka": TikiTaka(),
    "presion_alta": PresionAlta(),
    "contragolpe": Contragolpe(),
    "total": Total(),
    "jogo_bonito": JogoBonito(),
    "bloque_bajo": BloqueBajo(),
}

# ------------------------------------------------------------
#  Funciones de compatibilidad (antes en backend/tactics.py)
# ------------------------------------------------------------
def aplicar_tactica_a_equipo(equipo, tactica_nombre, pelota, dt):
    """
    Aplica una táctica a un equipo.
    """
    clase_tactica = TACTICAS_CLASES.get(tactica_nombre)
    if clase_tactica is None:
        clase_tactica = TikiTaka  # fallback
    equipo.tactica_obj = clase_tactica()
    equipo.tactica_actual = tactica_nombre

def obtener_distancia_presion(equipo):
    return getattr(equipo, 'distancia_presion', 200)

def obtener_factor_posesion(equipo):
    tactica_nombre = getattr(equipo, 'tactica_actual', 'tiki_taka')
    tactica = TACTICAS.get(tactica_nombre)
    return tactica.obtener_param("posesion", 0.5) if tactica else 0.5

def obtener_factor_pase_largo(equipo):
    tactica_nombre = getattr(equipo, 'tactica_actual', 'tiki_taka')
    tactica = TACTICAS.get(tactica_nombre)
    return tactica.obtener_param("pase_largo", 0.5) if tactica else 0.5

def obtener_frecuencia_regate(equipo):
    tactica_nombre = getattr(equipo, 'tactica_actual', 'tiki_taka')
    tactica = TACTICAS.get(tactica_nombre)
    return tactica.obtener_param("regate_frecuencia", 0.5) if tactica else 0.5

def obtener_profundidad_defensiva(equipo):
    return getattr(equipo, 'profundidad_defensiva', 0.5)

def obtener_altura_delanteros_defensiva(equipo):
    return getattr(equipo, 'altura_delanteros_defensiva', 0.5)

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

def actualizar_tactica_segun_marcador(equipo, goles_favor, goles_contra, tiempo_restante, minuto_total=90):
    """
    Cambia la táctica del equipo según el marcador y el tiempo.
    """
    tactica_nombre = seleccionar_tactica_por_marcador(goles_favor, goles_contra, tiempo_restante, minuto_total)
    if tactica_nombre != getattr(equipo, 'tactica_actual', None):
        aplicar_tactica_a_equipo(equipo, tactica_nombre, None, 0)
        return True
    return False

def obtener_formacion_para_tactica(tactica_nombre):
    """
    Devuelve una formación para una táctica dada (compatibilidad).
    """
    if tactica_nombre in ["catenaccio", "bloque_bajo"]:
        return [(0.85, 0.5), (0.7, 0.2), (0.7, 0.35), (0.7, 0.65), (0.7, 0.8),
                (0.55, 0.2), (0.55, 0.4), (0.55, 0.6), (0.55, 0.8),
                (0.4, 0.3), (0.4, 0.7)]
    elif tactica_nombre in ["presion_alta", "total"]:
        return [(0.9, 0.5), (0.8, 0.15), (0.8, 0.35), (0.8, 0.65), (0.8, 0.85),
                (0.6, 0.15), (0.6, 0.4), (0.6, 0.6), (0.6, 0.85),
                (0.4, 0.25), (0.4, 0.75)]
    else:
        from .base import FORMACION_LOCAL
        return FORMACION_LOCAL

# ------------------------------------------------------------
#  Exportación explícita para que `from .tactics import *` funcione
# ------------------------------------------------------------
__all__ = [
    'TacticaBase',
    'Catenaccio',
    'TikiTaka',
    'PresionAlta',
    'Contragolpe',
    'Total',
    'JogoBonito',
    'BloqueBajo',
    'TACTICAS_CLASES',
    'TACTICAS',
    'aplicar_tactica_a_equipo',
    'obtener_distancia_presion',
    'obtener_factor_posesion',
    'obtener_factor_pase_largo',
    'obtener_frecuencia_regate',
    'obtener_profundidad_defensiva',
    'obtener_altura_delanteros_defensiva',
    'seleccionar_tactica_por_marcador',
    'actualizar_tactica_segun_marcador',
    'obtener_formacion_para_tactica',
]